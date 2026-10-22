"""Zetlight Horizon Aqua LED — local UDP integration for Home Assistant.

Pure local control: binds a UDP socket, sends ``EE...CC`` request frames to the
device on port 8855 and parses ``DD...CC`` replies. No cloud, no Bluetooth.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import protocol
from .const import (
    CONF_DEVICE_CODE,
    CONF_PRESETS,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_SECONDS,
    DISCOVERY_TIMEOUT,
    DOMAIN,
    FEEDING_DEFAULT_LEVEL,
    FEEDING_DEFAULT_MINUTES,
    LIGHTNING_DEFAULT_FLASHES,
    LIGHTNING_DEFAULT_INTENSITY,
    LIGHTNING_DEFAULT_ON_MS,
    REQUEST_TIMEOUT,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
]


class ZetlightUDPError(Exception):
    """Raised when a UDP request fails or times out."""


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """Collects beacon datagrams during a discovery broadcast."""

    def __init__(self) -> None:
        self.found: dict[str, bytes] = {}

    def datagram_received(self, data: bytes, addr) -> None:  # noqa: ANN001
        if data[:1] == b"\xdd":
            self.found.setdefault(addr[0], data)


async def async_discover(hass: HomeAssistant, timeout: float = DISCOVERY_TIMEOUT) -> list[dict]:
    """Broadcast the discovery probe and return [{host, device_code, name}]."""
    loop = asyncio.get_running_loop()
    try:
        transport, proto = await loop.create_datagram_endpoint(
            _DiscoveryProtocol,
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )
    except OSError as err:
        _LOGGER.debug("Discovery socket error: %s", err)
        return []
    results: list[dict] = []
    try:
        transport.sendto(protocol.DISCOVERY_FRAME, ("255.255.255.255", DEFAULT_PORT))
        await asyncio.sleep(timeout)
        for host, data in proto.found.items():  # type: ignore[attr-defined]
            try:
                code, name = protocol.parse_beacon(data)
            except ValueError:
                continue
            results.append(
                {"host": host, "device_code": code.hex().upper(), "name": name}
            )
    finally:
        transport.close()
    return results


class _ClientProtocol(asyncio.DatagramProtocol):
    """Minimal datagram protocol that resolves one pending reply at a time.

    An optional expected command byte lets a read ignore unrelated datagrams
    (e.g. the device's broadcast heartbeats, or a late ACK) and wait for the
    matching reply.
    """

    def __init__(self) -> None:
        self._pending: asyncio.Future[bytes] | None = None
        self._expect_cmd: int | None = None

    def set_pending(self, future: asyncio.Future[bytes], expect_cmd: int | None) -> None:
        self._pending = future
        self._expect_cmd = expect_cmd

    def datagram_received(self, data: bytes, addr) -> None:  # noqa: ANN001
        if self._pending is None or self._pending.done():
            return
        if self._expect_cmd is not None and not (
            len(data) >= 8 and data[0] == protocol.RESPONSE_HEADER
            and data[7] == self._expect_cmd
        ):
            return  # not the reply we're waiting for; keep listening
        self._pending.set_result(data)

    def error_received(self, exc: Exception) -> None:
        if self._pending is not None and not self._pending.done():
            self._pending.set_exception(exc)


class ZetlightClient:
    """Async UDP client for a single M5 device.

    All request/response round trips are serialized through a lock because the
    device shares one reply slot, matching how the vendor app drives the link.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        device_code: bytes,
    ) -> None:
        self._hass = hass
        self._host = host
        self._port = port
        self.device_code = device_code
        self._transport: asyncio.DatagramTransport | None = None
        self._proto: _ClientProtocol | None = None
        self._lock = asyncio.Lock()

    async def async_connect(self) -> None:
        """Open the UDP endpoint, binding 8855 if free, else an ephemeral port.

        Port 8855 may already be in use on the host; UDP replies come back to
        the socket's source port either way, so falling back to port 0 is fine.
        """
        loop = asyncio.get_running_loop()
        for local_port in (self._port, 0):
            try:
                transport, proto = await loop.create_datagram_endpoint(
                    _ClientProtocol,
                    local_addr=("0.0.0.0", local_port),
                    remote_addr=(self._host, self._port),
                )
            except OSError as err:
                if local_port == 0:
                    raise ZetlightUDPError(f"cannot open UDP socket: {err}") from err
                _LOGGER.debug("Local port %s busy, falling back to ephemeral", local_port)
                continue
            self._transport = transport
            self._proto = proto  # type: ignore[assignment]
            return

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def _request(
        self, frame: bytes, *, expect_reply: bool, expect_cmd: int | None = None
    ) -> bytes | None:
        if self._transport is None or self._proto is None:
            raise ZetlightUDPError("client not connected")
        async with self._lock:
            loop = asyncio.get_running_loop()
            future: asyncio.Future[bytes] = loop.create_future()
            self._proto.set_pending(future, expect_cmd)
            self._transport.sendto(frame)
            if not expect_reply:
                return None
            try:
                return await asyncio.wait_for(future, timeout=REQUEST_TIMEOUT)
            except asyncio.TimeoutError as err:
                raise ZetlightUDPError("no reply from device") from err

    async def async_read_status(self) -> protocol.DeviceStatus:
        """Send 0x0C and parse the reply. Also confirms the device code."""
        frame = protocol.build_read_status(device_code=self.device_code)
        reply = await self._request(
            frame, expect_reply=True, expect_cmd=protocol.CMD_READ_STATUS
        )
        assert reply is not None
        status = protocol.parse_status(reply)
        # The device echoes its real code; adopt it so later commands match.
        self.device_code = status.device_code
        return status

    async def async_turn_on(self) -> None:
        """Send the verified ON/START frame (0x1E). Fire-and-forget."""
        await self._request(
            protocol.build_on(device_code=self.device_code), expect_reply=False
        )

    async def async_turn_off(self) -> None:
        """Send the verified OFF frame (0x1F). Fire-and-forget."""
        await self._request(
            protocol.build_off(device_code=self.device_code), expect_reply=False
        )

    async def async_set_brightness(self, channels: tuple[int, int, int, int]) -> None:
        """Send a 0x13 dimming frame (each channel 0-100). Fire-and-forget.

        Real-time preview only; does not persist to the device's stored program.
        """
        await self._request(
            protocol.build_brightness(channels, device_code=self.device_code),
            expect_reply=False,
        )

    async def async_sync_time(self, now) -> None:  # noqa: ANN001
        """Send the device clock (0x03) from a datetime. Fire-and-forget."""
        await self._request(
            protocol.build_time_sync(
                now.year, now.month, now.day, now.hour, now.minute, now.second,
                device_code=self.device_code,
            ),
            expect_reply=False,
        )

    async def async_write_brightness(
        self, slots: list[tuple[int, int, int, int]]
    ) -> None:
        """Write only the schedule brightness (0x1C) and apply, keeping times."""
        await self._request(
            protocol.build_schedule_brightness(slots, device_code=self.device_code),
            expect_reply=False,
        )
        await asyncio.sleep(0.1)
        await self._request(
            protocol.build_on(device_code=self.device_code), expect_reply=False
        )

    async def async_read_config(self) -> bytes:
        """Send 0x10 and return the raw reply (schedule config)."""
        reply = await self._request(
            protocol.build_read_config(device_code=self.device_code),
            expect_reply=True,
            expect_cmd=protocol.CMD_READ_CONFIG,
        )
        assert reply is not None
        return reply

    async def async_read_options(self) -> protocol.OptionState:
        """Send 0x20 and parse the option/mode state."""
        reply = await self._request(
            protocol.build_read_options(device_code=self.device_code),
            expect_reply=True,
            expect_cmd=protocol.CMD_READ_OPTIONS,
        )
        assert reply is not None
        return protocol.parse_options(reply)

    async def async_set_coral(self, on: bool) -> None:
        """Enable/disable the device's native coral-acclimation mode (0x14).

        Preserves the auto-cloud and phase switches read from 0x20.
        """
        try:
            current = await self.async_read_options()
            auto_cloud, phase = current.auto_cloud, current.phase
        except (ZetlightUDPError, ValueError):
            auto_cloud = phase = 0
        await self._request(
            protocol.build_set_options(
                auto_cloud, phase, 1 if on else 0, device_code=self.device_code
            ),
            expect_reply=False,
        )

    async def async_set_auto_cloud(self, on: bool) -> None:
        """Enable/disable auto-clouds (0x14), preserving phase and coral."""
        try:
            cur = await self.async_read_options()
            phase, coral = cur.phase, cur.coral
        except (ZetlightUDPError, ValueError):
            phase = coral = 0
        await self._request(
            protocol.build_set_options(
                1 if on else 0, phase, coral, device_code=self.device_code
            ),
            expect_reply=False,
        )

    async def async_set_moon(self, on: bool) -> None:
        """Enable/disable moon-phase mode (0x19)."""
        await self._request(
            protocol.build_set_moon(on, device_code=self.device_code),
            expect_reply=False,
        )

    async def async_set_fade(self, on: bool, minutes: int) -> None:
        """Set the gradient/fade time (0x22): [enable, minutes]."""
        await self._request(
            protocol.build_set_fade(on, minutes, device_code=self.device_code),
            expect_reply=False,
        )

    async def async_write_schedule(
        self,
        slots: list[tuple[int, int, int, int]],
        start_minute: int,
        durations: list[int],
    ) -> None:
        """Write the full daily schedule: times (0x11) then brightness (0x1C).

        WARNING: overwrites the device's stored time-curve program.
        """
        await self._request(
            protocol.build_schedule_times(
                start_minute, durations, device_code=self.device_code
            ),
            expect_reply=False,
        )
        await asyncio.sleep(0.1)
        await self._request(
            protocol.build_schedule_brightness(slots, device_code=self.device_code),
            expect_reply=False,
        )
        # Apply the saved program (0x1C alone does not refresh live output; the
        # vendor app does save -> start).
        await asyncio.sleep(0.1)
        await self._request(
            protocol.build_on(device_code=self.device_code), expect_reply=False
        )


class ZetlightCoordinator(DataUpdateCoordinator[protocol.DeviceStatus]):
    """Polls device status and holds the shared 4-channel dimming state.

    The 0x13 command sets all four channels at once, so the overall-brightness
    light and the per-channel number entities share one list of channel levels
    (0-100). Any change sends the full frame and notifies all entities.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: ZetlightClient,
        entry_id: str,
        update_interval=SCAN_INTERVAL,  # noqa: ANN001
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.channel_count = protocol.NUM_CHANNELS  # detected from 0x0C
        self._acclimation_store = Store(hass, 1, f"{DOMAIN}.{entry_id}.acclimation")
        self._acclimation_base: list[tuple] | None = None
        self._acclimation_loaded = False
        self.channels: list[int] = [0] * protocol.NUM_CHANNELS
        self._channels_seeded = False
        # Tunable custom-lightning parameters (set by number entities).
        self.lightning_flashes = LIGHTNING_DEFAULT_FLASHES
        self.lightning_intensity = LIGHTNING_DEFAULT_INTENSITY
        self.lightning_on_ms = LIGHTNING_DEFAULT_ON_MS
        self._lightning_lock = asyncio.Lock()
        # Acclimation: schedule writes are scaled by this percent (100 = off).
        self.acclimation_scale = 100
        # Feeding / maintenance mode state.
        self.feeding_level = FEEDING_DEFAULT_LEVEL
        self.feeding_minutes = FEEDING_DEFAULT_MINUTES
        self.feeding_on = False
        self._feeding_saved: list[int] | None = None
        self._feeding_unsub = None
        # Raw bytes of the last 0x10 config reply (for schedule decoding work).
        self.last_config: bytes | None = None
        # Parsed per-slot brightness from the last 0x10 reply (raw %), or None.
        self.schedule: list[tuple[int, int, int, int]] | None = None
        # Last parsed option state (0x20), or None.
        self.options: protocol.OptionState | None = None

    async def _async_update_data(self) -> protocol.DeviceStatus:
        try:
            status = await self.client.async_read_status()
        except ZetlightUDPError as err:
            raise UpdateFailed(str(err)) from err
        # Seed the channel state once from the device's reported setpoints so
        # the sliders start at sensible values. These are the current program
        # setpoints, not live on/off state (see docs §6).
        self.channel_count = len(status.setpoints) or protocol.NUM_CHANNELS
        if not self._channels_seeded:
            self.channels = [max(0, min(100, s)) for s in status.setpoints]
            self._channels_seeded = True
        # Best-effort schedule read (0x10); don't fail the update if it errors.
        try:
            raw = await self.client.async_read_config()
            self.last_config = raw
            self.schedule = protocol.parse_schedule_brightness(raw)
        except (ZetlightUDPError, ValueError) as err:
            _LOGGER.debug("Schedule read failed: %s", err)
        try:
            self.options = await self.client.async_read_options()
        except (ZetlightUDPError, ValueError) as err:
            _LOGGER.debug("Option read failed: %s", err)
        return status

    async def async_set_coral(self, on: bool) -> None:
        """Toggle the device's native coral-acclimation mode and refresh."""
        await self.client.async_set_coral(on)
        await self._refresh_options()

    async def async_set_auto_cloud(self, on: bool) -> None:
        """Toggle auto-clouds and refresh."""
        await self.client.async_set_auto_cloud(on)
        await self._refresh_options()

    async def async_set_moon(self, on: bool) -> None:
        """Toggle moon-phase mode and refresh."""
        await self.client.async_set_moon(on)
        await self._refresh_options()

    async def async_set_fade(self, on: bool, minutes: int) -> None:
        """Set the gradient/fade time and refresh."""
        await self.client.async_set_fade(on, minutes)
        await self._refresh_options()

    async def _refresh_options(self) -> None:
        await asyncio.sleep(0.2)
        try:
            self.options = await self.client.async_read_options()
        except (ZetlightUDPError, ValueError):
            pass
        self.async_update_listeners()

    async def async_apply_channels(self) -> None:
        """Send the current channel state as a 0x13 frame and notify entities."""
        await self.client.async_set_brightness(tuple(self.channels))
        self.async_update_listeners()

    async def async_set_channel(self, index: int, value: int) -> None:
        """Set one channel (0-100) and apply."""
        self.channels[index] = max(0, min(100, value))
        await self.async_apply_channels()

    async def async_set_all(self, level: int) -> None:
        """Set all channels to the same level (0-100) and apply."""
        self.channels = [max(0, min(100, level))] * self.channel_count
        await self.async_apply_channels()

    async def async_lightning(self) -> None:
        """Run a custom lightning effect using live 0x13 frames.

        Flashes white (A) + blue (B) only — no purple afterglow like the app's
        built-in effect — then restores the pre-flash channel levels. Real-time
        preview only; the stored program is untouched. Count/intensity/on-time
        come from the tunable number entities.
        """
        async with self._lightning_lock:
            saved = tuple(self.channels)
            strokes = max(1, int(self.lightning_flashes))
            peak = max(1, min(100, int(self.lightning_intensity)))
            on_s = max(0.02, int(self.lightning_on_ms) / 1000)
            nch = len(saved)
            ru = random.uniform
            rnd = random.random

            def vec(level: float) -> tuple[int, ...]:
                # white + blue (first two channels) only; the rest off
                lvl = max(0, min(100, int(level)))
                return tuple(lvl if i < 2 else 0 for i in range(nch))

            dark = tuple(0 for _ in range(nch))

            async def flash(level: float) -> None:
                await self.client.async_set_brightness(vec(level))

            async def strike(lo: float, hi: float) -> None:
                await flash(peak)
                await asyncio.sleep(on_s * ru(lo, hi))
                await self.client.async_set_brightness(dark)
                await asyncio.sleep(ru(0.015, 0.035))

            # Disable fade so the strikes are sharp, then restore the user's
            # setting afterwards (a long fade would otherwise smear the flash).
            fade = None
            try:
                fade = await self.client.async_read_options()
                if fade.fade_enable:
                    await self.client.async_set_fade(False, fade.fade_minutes)
            except (ZetlightUDPError, ValueError):
                fade = None

            try:
                # faint pre-flash + short tense pause (sometimes skipped)
                if rnd() < 0.8:
                    await flash(ru(12, 28))
                    await asyncio.sleep(ru(0.02, 0.04))
                    await self.client.async_set_brightness(dark)
                    await asyncio.sleep(ru(0.08, 0.18))
                # blinding main, then 1-2 hard extra hits (random)
                await strike(1.5, 2.1)
                for _ in range(random.randint(1, 2)):
                    await strike(0.6, 1.0)
                # irregular machine-gun flicker burst
                for _ in range(max(2, strokes) + random.randint(0, 2)):
                    await flash(peak if rnd() < 0.6 else ru(55, 95))
                    await asyncio.sleep(on_s * ru(0.3, 0.6))
                    await self.client.async_set_brightness(dark)
                    await asyncio.sleep(ru(0.015, 0.05))
                # occasional sustained "sheet" flash
                if rnd() < 0.4:
                    await flash(peak)
                    await asyncio.sleep(ru(0.15, 0.28))
                    await self.client.async_set_brightness(dark)
                    await asyncio.sleep(ru(0.03, 0.07))
                # random second wave (keeps repeats from feeling mechanical)
                if rnd() < 0.45:
                    await asyncio.sleep(ru(0.12, 0.28))
                    await strike(1.0, 1.5)
                    for _ in range(random.randint(1, 3)):
                        await flash(ru(50, 95))
                        await asyncio.sleep(on_s * ru(0.3, 0.6))
                        await self.client.async_set_brightness(dark)
                        await asyncio.sleep(ru(0.02, 0.06))
                # short afterglow fade back to normal
                glow = vec(int(peak * 0.45))
                for i in (1, 2, 3):
                    frac = i / 3
                    vals = tuple(
                        round(glow[j] + (saved[j] - glow[j]) * frac) for j in range(nch)
                    )
                    await self.client.async_set_brightness(vals)
                    await asyncio.sleep(0.05)
            finally:
                await self.client.async_set_brightness(saved)
                if fade is not None and fade.fade_enable:
                    try:
                        await self.client.async_set_fade(True, fade.fade_minutes)
                    except ZetlightUDPError:
                        pass

    async def async_cloud(self) -> None:
        """Custom passing-cloud effect: ramp all channels down, hold, ramp up.

        Built from live 0x13 frames; restores the previous levels afterwards.
        """
        async with self._lightning_lock:
            saved = tuple(self.channels)
            target = tuple(int(c * 0.4) for c in saved)
            nch = len(saved)
            steps = 8
            try:
                for i in range(1, steps + 1):
                    vals = tuple(
                        int(saved[j] + (target[j] - saved[j]) * i / steps)
                        for j in range(nch)
                    )
                    await self.client.async_set_brightness(vals)
                    await asyncio.sleep(0.18)
                await asyncio.sleep(2.0)
                for i in range(1, steps + 1):
                    vals = tuple(
                        int(target[j] + (saved[j] - target[j]) * i / steps)
                        for j in range(nch)
                    )
                    await self.client.async_set_brightness(vals)
                    await asyncio.sleep(0.18)
            finally:
                await self.client.async_set_brightness(saved)

    async def async_feeding_set(self, on: bool) -> None:
        """Toggle feeding mode: dim to the feeding level, auto-restore on timeout."""
        if self._feeding_unsub is not None:
            self._feeding_unsub()
            self._feeding_unsub = None
        if on:
            if not self.feeding_on:
                self._feeding_saved = list(self.channels)
            self.feeding_on = True
            level = max(0, min(100, int(self.feeding_level)))
            self.channels = [level] * self.channel_count
            await self.async_apply_channels()
            self._feeding_unsub = async_call_later(
                self.hass, max(1, int(self.feeding_minutes)) * 60, self._feeding_timeout
            )
        else:
            self.feeding_on = False
            if self._feeding_saved is not None:
                self.channels = self._feeding_saved
                self._feeding_saved = None
            await self.async_apply_channels()
        self.async_update_listeners()

    @callback
    def _feeding_timeout(self, _now) -> None:  # noqa: ANN001
        self._feeding_unsub = None
        self.hass.async_create_task(self.async_feeding_set(False))

    async def async_write_schedule(
        self,
        slots: list[tuple[int, int, int, int]],
        start_minute: int,
        durations: list[int],
    ) -> None:
        """Write the daily schedule exactly as given (overwrites stored program)."""
        await self.client.async_write_schedule(slots, start_minute, durations)

    async def async_apply_acclimation(self, value: int) -> None:
        """Scale the stored schedule's brightness to ``value`` percent.

        Non-destructive to the user's configured curve: the first time it is
        engaged (below 100), the current schedule is snapshotted as the base and
        remembered; every change rescales from that base, and 100% writes the
        base back (full restore). It is persistent — it stays until changed, not
        auto-timed (that is feeding mode).
        """
        value = max(10, min(100, int(value)))
        self.acclimation_scale = value
        await self._load_acclimation_base()
        if value == 100 and self._acclimation_base is None:
            # already at full and nothing was scaled — nothing to do
            self.async_update_listeners()
            return
        if self._acclimation_base is None:
            if not self.schedule:
                raise HomeAssistantError(
                    "cannot read the current schedule to acclimate from"
                )
            self._acclimation_base = [tuple(s) for s in self.schedule]
            await self._acclimation_store.async_save(
                {"base": [list(s) for s in self._acclimation_base]}
            )
        base = self._acclimation_base
        scaled = [
            tuple(min(255, round(c * value / 100)) for c in slot) for slot in base
        ]
        await self.client.async_write_brightness(scaled)
        if value == 100:
            # fully restored — forget the base so a later lowering re-snapshots
            # the (possibly updated) configured schedule.
            self._acclimation_base = None
            await self._acclimation_store.async_remove()
        self.async_update_listeners()

    async def _load_acclimation_base(self) -> None:
        if self._acclimation_loaded:
            return
        data = await self._acclimation_store.async_load()
        if data and data.get("base"):
            self._acclimation_base = [tuple(s) for s in data["base"]]
        self._acclimation_loaded = True

    async def async_read_config(self) -> bytes:
        """Read the raw 0x10 config reply and cache it."""
        self.last_config = await self.client.async_read_config()
        return self.last_config


type ZetlightConfigEntry = ConfigEntry[ZetlightCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ZetlightConfigEntry) -> bool:
    """Set up a Zetlight device from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    device_code = bytes.fromhex(entry.data[CONF_DEVICE_CODE])

    client = ZetlightClient(hass, host, port, device_code)
    await client.async_connect()

    interval = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_SECONDS)
    )
    coordinator = ZetlightCoordinator(hass, client, entry.entry_id, interval)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        client.close()
        raise

    entry.runtime_data = coordinator

    # Best-effort: sync the device clock to Home Assistant's local time.
    try:
        await client.async_sync_time(dt_util.now())
    except ZetlightUDPError as err:
        _LOGGER.debug("Initial clock sync failed: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ZetlightConfigEntry
) -> None:
    """Reload the entry when options (e.g. presets) change."""
    await hass.config_entries.async_reload(entry.entry_id)


SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SYNC_CLOCK = "sync_clock"

_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("start"): cv.string,  # "HH:MM"
        vol.Required("durations"): vol.All(
            cv.ensure_list,
            [vol.All(vol.Coerce(int), vol.Range(min=0, max=1439))],
            vol.Length(min=protocol.NUM_SLOTS, max=protocol.NUM_SLOTS),
        ),
        vol.Required("brightness"): vol.All(
            cv.ensure_list,
            [
                vol.All(
                    cv.ensure_list,
                    # 0-200: values above 100 are overdrive (device-supported).
                    [vol.All(vol.Coerce(int), vol.Range(min=0, max=200))],
                    vol.Length(min=protocol.NUM_CHANNELS, max=protocol.NUM_CHANNELS),
                )
            ],
            vol.Length(min=protocol.NUM_SLOTS, max=protocol.NUM_SLOTS),
        ),
    }
)


def _parse_hhmm(value: str) -> int:
    """Parse 'HH:MM' into minutes from midnight."""
    try:
        hh, mm = value.split(":")
        minutes = int(hh) * 60 + int(mm)
    except (ValueError, AttributeError) as err:
        raise HomeAssistantError(f"invalid time '{value}', expected HH:MM") from err
    if not 0 <= minutes < 1440:
        raise HomeAssistantError(f"time out of range: {value}")
    return minutes


def preset_to_args(preset: dict) -> tuple[list[tuple], int, list[int]]:
    """Convert a preset dict into (slots, start_minute, durations).

    Raises HomeAssistantError on malformed data.
    """
    try:
        start = _parse_hhmm(preset["start"])
        durations = [int(d) for d in preset["durations"]]
        slots = [tuple(int(x) for x in s) for s in preset["brightness"]]
    except (KeyError, TypeError, ValueError) as err:
        raise HomeAssistantError(f"invalid preset: {err}") from err
    if len(durations) != protocol.NUM_SLOTS or len(slots) != protocol.NUM_SLOTS:
        raise HomeAssistantError(f"preset needs {protocol.NUM_SLOTS} slots")
    for slot in slots:
        if len(slot) != protocol.NUM_CHANNELS:
            raise HomeAssistantError(f"each slot needs {protocol.NUM_CHANNELS} values")
    return slots, start, durations


def _loaded_coordinators(hass: HomeAssistant) -> list[ZetlightCoordinator]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register the integration's services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    async def handle_set_schedule(call: ServiceCall) -> None:
        start = _parse_hhmm(call.data["start"])
        durations = list(call.data["durations"])
        slots = [tuple(slot) for slot in call.data["brightness"]]
        coordinators = _loaded_coordinators(hass)
        if not coordinators:
            raise HomeAssistantError("no Zetlight device is loaded")
        for coordinator in coordinators:
            try:
                await coordinator.async_write_schedule(slots, start, durations)
            except ZetlightUDPError as err:
                raise HomeAssistantError(f"failed to write schedule: {err}") from err

    async def handle_sync_clock(call: ServiceCall) -> None:
        coordinators = _loaded_coordinators(hass)
        if not coordinators:
            raise HomeAssistantError("no Zetlight device is loaded")
        for coordinator in coordinators:
            try:
                await coordinator.client.async_sync_time(dt_util.now())
            except ZetlightUDPError as err:
                raise HomeAssistantError(f"failed to sync clock: {err}") from err

    hass.services.async_register(
        DOMAIN, SERVICE_SET_SCHEDULE, handle_set_schedule, schema=_SET_SCHEDULE_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_SYNC_CLOCK, handle_sync_clock)


async def async_unload_entry(hass: HomeAssistant, entry: ZetlightConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.client.close()
        # Drop the shared services once the last entry is gone.
        loaded = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.state.recoverable
        ]
        if not loaded:
            for service in (SERVICE_SET_SCHEDULE, SERVICE_SYNC_CLOCK):
                hass.services.async_remove(DOMAIN, service)
    return unload_ok
