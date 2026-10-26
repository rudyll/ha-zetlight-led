"""Zetlight Horizon Aqua LED — local UDP integration for Home Assistant.

Pure local control: binds a UDP socket, sends ``EE...CC`` request frames to the
device on port 8855 and parses ``DD...CC`` replies. No cloud, no Bluetooth.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
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
        self._option_lock = asyncio.Lock()

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
        # Applying output belongs to the coordinator's active-mode priority.

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
        """Read-modify-write only from a valid snapshot; serialize sibling edits."""
        async with self._option_lock:
            try:
                current = await self.async_read_options()
            except (ZetlightUDPError, ValueError) as err:
                raise ZetlightUDPError("cannot preserve current options; coral unchanged") from err
            if on and current.phase != 0:
                raise ZetlightUDPError("Disable lunar phase before enabling native coral acclimation")
            await self._request(protocol.build_set_options(
                current.auto_cloud, current.phase, 1 if on else 0, device_code=self.device_code), expect_reply=False)

    async def async_set_auto_cloud(self, on: bool) -> None:
        """Read-modify-write only from a valid snapshot; serialize sibling edits."""
        async with self._option_lock:
            try:
                current = await self.async_read_options()
            except (ZetlightUDPError, ValueError) as err:
                raise ZetlightUDPError("cannot preserve current options; auto-cloud unchanged") from err
            await self._request(protocol.build_set_options(
                1 if on else 0, current.phase, current.coral, device_code=self.device_code), expect_reply=False)

    async def async_set_lunar_phase(self, on: bool) -> protocol.OptionState:
        """Change only the phase byte, then confirm it and preserved sibling flags."""
        async with self._option_lock:
            try:
                current = await self.async_read_options()
            except (ZetlightUDPError, ValueError) as err:
                raise ZetlightUDPError("cannot preserve current options; lunar phase unchanged") from err
            if on and current.coral > 0:
                raise ZetlightUDPError("Disable native coral acclimation before enabling lunar phase")
            await self._request(protocol.build_set_options(
                current.auto_cloud, 1 if on else 0, current.coral,
                device_code=self.device_code), expect_reply=False)
            await asyncio.sleep(0.2)
            try:
                observed = await self.async_read_options()
            except (ZetlightUDPError, OSError, ValueError) as err:
                raise ZetlightUDPError("lunar phase update unconfirmed; options readback failed") from err
            if (observed.phase != int(on) or observed.auto_cloud != current.auto_cloud
                    or observed.coral != current.coral):
                raise ZetlightUDPError("lunar phase update unconfirmed; inspect device options")
            return observed

    async def async_set_moon(self, on: bool) -> None:
        """Enable/disable native Moon Light (0x19); retain the legacy method."""
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
        # The coordinator verifies the curve, then applies the active intent.
        # START here would briefly override off/feeding/viewing modes.


class _EffectInterrupted(Exception):
    pass


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
        self._mode_lock = asyncio.Lock()
        self._generation = 0
        self._fade_generation = 0
        self._power_off = False
        self._manual_channels = None
        self._closed = False
        self.command_error = None
        self._feeding_deadline = None
        self._feeding_store = Store(hass, 1, f"{DOMAIN}.{entry_id}.feeding")
        self._pending_schedule = None
        self._pending_scale = None
        self.channel_count = protocol.NUM_CHANNELS  # detected from 0x0C
        self._acclimation_store = Store(hass, 1, f"{DOMAIN}.{entry_id}.acclimation")
        self._acclimation_base: list[tuple] | None = None
        self._acclimation_loaded = False
        self._acclimation_has_scale = False
        self.schedule_conflict = False
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
        self._feeding_unsub = None
        self._control_retry_unsub = None
        # Viewing / photo mode state.
        self.viewing_on = False
        self._viewing_started_at = None
        self._viewing_deadline = None
        self._viewing_unsub = None
        self.schedule_timing = None
        self.schedule_timing_read_at = None
        self.viewing_levels: dict[int, int] = {}
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
            self.channels = [max(0, min(self.channel_limit, s)) for s in status.setpoints]
            self._channels_seeded = True
        # Best-effort schedule read (0x10); don't fail the update if it errors.
        try:
            raw = await self.client.async_read_config()
            self.last_config = raw
            self.schedule = protocol.parse_schedule_brightness(raw)
            try:
                self.schedule_timing = protocol.parse_schedule_timing(raw)
                self.schedule_timing_read_at = time.time()
            except ValueError:
                self.schedule_timing = None
                self.schedule_timing_read_at = None
        except (ZetlightUDPError, ValueError) as err:
            self.schedule_timing = None
            self.schedule_timing_read_at = None
            _LOGGER.debug("Schedule read failed: %s", err)
        await self._shorten_viewing_deadline()
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

    async def async_set_lunar_phase(self, on: bool) -> None:
        """Toggle native Lunar Phase and refresh actual option readback."""
        try:
            observed = await self.client.async_set_lunar_phase(on)
        except (ZetlightUDPError, OSError, ValueError, asyncio.CancelledError):
            # The write may have reached the lamp; do not display a stale flag.
            self.options = None
            self.async_update_listeners()
            raise
        self.options = observed
        self.async_update_listeners()

    async def async_set_moon(self, on: bool) -> None:
        """Toggle native Moon Light and refresh; existing callers stay compatible."""
        await self.client.async_set_moon(on)
        await self._refresh_options()

    async def async_set_fade(self, on: bool, minutes: int) -> None:
        """Set the gradient/fade time and refresh."""
        self._fade_generation += 1
        async with self._mode_lock:
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
        self._generation += 1
        async with self._mode_lock:
            channels = list(self._manual_channels or self.channels)
            if type(value) is not int or not 0 <= value <= self.channel_limit:
                raise HomeAssistantError("channel outside verified model range")
            channels[index] = value
            self._manual_channels = channels
            self._power_off = False
            await self._apply_and_save_control()

    async def async_set_all(self, level: int) -> None:
        self._generation += 1
        async with self._mode_lock:
            if type(level) is not int or not 0 <= level <= self.channel_limit:
                raise HomeAssistantError("brightness outside verified model range")
            self._manual_channels = [level] * self.channel_count
            self._power_off = False
            await self._apply_and_save_control()

    async def async_lightning(self) -> None:
        """Run a custom lightning effect using live 0x13 frames.

        Flashes white (A) + blue (B) only — no purple afterglow like the app's
        built-in effect — then restores the pre-flash channel levels. Real-time
        preview only; the stored program is untouched. Count/intensity/on-time
        come from the tunable number entities.
        """
        async with self._lightning_lock:
            generation = self._generation
            fade_generation = self._fade_generation
            if self._closed or self.active_mode not in ["schedule", "manual"]:
                return
            saved = tuple(self.channels)
            strokes = max(1, int(self.lightning_flashes))
            peak = max(1, min(self.channel_limit, int(self.lightning_intensity)))
            on_s = max(0.02, int(self.lightning_on_ms) / 1000)
            nch = len(saved)
            ru = random.uniform
            rnd = random.random

            def vec(level: float) -> tuple[int, ...]:
                # first two channels (A+B) only; the rest off
                lvl = max(0, min(100, int(level)))
                return tuple(lvl if i < 2 else 0 for i in range(nch))

            dark = tuple(0 for _ in range(nch))

            async def flash(level: float) -> None:
                await self._effect_set_brightness(vec(level), generation)

            async def strike(lo: float, hi: float) -> None:
                await flash(peak)
                await asyncio.sleep(on_s * ru(lo, hi))
                await self._effect_set_brightness(dark, generation)
                await asyncio.sleep(ru(0.015, 0.035))

            # Disable fade so the strikes are sharp, then restore the user's
            # setting afterwards (a long fade would otherwise smear the flash).
            try:
                fade = await self._begin_effect(generation)
            except _EffectInterrupted:
                return

            try:
                # faint pre-flash + short tense pause (sometimes skipped)
                if rnd() < 0.8:
                    await flash(ru(12, 28))
                    await asyncio.sleep(ru(0.02, 0.04))
                    await self._effect_set_brightness(dark, generation)
                    await asyncio.sleep(ru(0.08, 0.18))
                # blinding main, then 1-2 hard extra hits (random)
                await strike(1.5, 2.1)
                for _ in range(random.randint(1, 2)):
                    await strike(0.6, 1.0)
                # irregular machine-gun flicker burst
                for _ in range(max(2, strokes) + random.randint(0, 2)):
                    await flash(peak if rnd() < 0.6 else ru(55, 95))
                    await asyncio.sleep(on_s * ru(0.3, 0.6))
                    await self._effect_set_brightness(dark, generation)
                    await asyncio.sleep(ru(0.015, 0.05))
                # occasional sustained "sheet" flash
                if rnd() < 0.4:
                    await flash(peak)
                    await asyncio.sleep(ru(0.15, 0.28))
                    await self._effect_set_brightness(dark, generation)
                    await asyncio.sleep(ru(0.03, 0.07))
                # random second wave (keeps repeats from feeling mechanical)
                if rnd() < 0.45:
                    await asyncio.sleep(ru(0.12, 0.28))
                    await strike(1.0, 1.5)
                    for _ in range(random.randint(1, 3)):
                        await flash(ru(50, 95))
                        await asyncio.sleep(on_s * ru(0.3, 0.6))
                        await self._effect_set_brightness(dark, generation)
                        await asyncio.sleep(ru(0.02, 0.06))
                # short afterglow fade back to normal
                glow = vec(int(peak * 0.45))
                for i in (1, 2, 3):
                    frac = i / 3
                    vals = tuple(
                        round(glow[j] + (saved[j] - glow[j]) * frac) for j in range(nch)
                    )
                    await self._effect_set_brightness(vals, generation)
                    await asyncio.sleep(0.05)
            except _EffectInterrupted:
                pass
            finally:
                await self._finish_effect(generation, fade, fade_generation)

    async def _fade_suspend(self) -> "protocol.OptionState | None":
        """Read and temporarily disable the device fade (so live effects aren't
        smeared by a long gradient). Returns the state for _fade_resume."""
        try:
            fade = await self.client.async_read_options()
            if fade.fade_enable:
                await self.client.async_set_fade(False, fade.fade_minutes)
            return fade
        except (ZetlightUDPError, ValueError):
            return None

    async def _fade_resume(self, fade) -> None:  # noqa: ANN001
        if fade is not None and fade.fade_enable:
            try:
                await self.client.async_set_fade(True, fade.fade_minutes)
            except ZetlightUDPError:
                pass

    async def _resume_program(self) -> None:
        """Hand control back to the device's stored schedule program (0x1E START).

        A live 0x13 dim is a temporary preview that holds — it does NOT expire on
        its own, so after an effect the device would otherwise stay stuck at that
        level and never hit the schedule's next boundary (e.g. the nightly off).
        START re-arms the time-based program from the current clock, so the light
        follows the preset again — including turning off if the current slot is an
        off/sleep period. Then read the setpoints so the HA entities stay in sync.
        """
        await self.client.async_turn_on()  # 0x1E START = resume the program
        await asyncio.sleep(0.3)
        try:
            status = await self.client.async_read_status()
            self.channels = [max(0, min(self.channel_limit, s)) for s in status.setpoints]
        except (ZetlightUDPError, ValueError):
            pass
        self.async_update_listeners()

    async def _ramp(self, start, end, steps: int, total: float, generation) -> None:  # noqa: ANN001
        """Smoothly interpolate channel levels from start to end (ease in/out)."""
        nch = len(start)
        for i in range(1, steps + 1):
            t = i / steps
            e = t * t * (3 - 2 * t)  # smoothstep
            vals = tuple(round(start[j] + (end[j] - start[j]) * e) for j in range(nch))
            await self._effect_set_brightness(vals, generation)
            await asyncio.sleep(total / steps)

    async def async_cloud(self) -> None:
        """Custom passing-cloud effect: one or two clouds drift over, dimming to
        a random depth with a smooth ease, holding, then clearing.

        Built from live 0x13 frames; disables fade for the duration (a long fade
        would smear it) and restores the previous levels + fade afterwards.
        """
        async with self._lightning_lock:
            generation = self._generation
            fade_generation = self._fade_generation
            if self._closed or self.active_mode not in ["schedule", "manual"]:
                return
            saved = tuple(self.channels)
            try:
                fade = await self._begin_effect(generation)
            except _EffectInterrupted:
                return
            try:
                for _ in range(random.randint(1, 2)):
                    depth = random.uniform(0.25, 0.7)  # dim to 25-70% of current
                    target = tuple(int(c * depth) for c in saved)
                    await self._ramp(saved, target, 12, random.uniform(2.0, 4.0), generation)
                    await asyncio.sleep(random.uniform(2.0, 5.0))  # overcast
                    await self._ramp(target, saved, 12, random.uniform(2.0, 4.0), generation)
                    await asyncio.sleep(random.uniform(0.6, 2.0))  # gap between clouds
            except _EffectInterrupted:
                pass
            finally:
                await self._finish_effect(generation, fade, fade_generation)

    async def async_feeding_set(self, on: bool) -> None:
        self._generation += 1
        async with self._mode_lock:
            if self._closed:
                raise HomeAssistantError("integration unloaded")
            deadline = time.time() + max(1, int(self.feeding_minutes)) * 60 if on else None
            # Save the obligation before changing hardware or losing the timer.
            await self._save_control(deadline, True)
            self.feeding_on = on
            self._feeding_deadline = deadline
            self._arm_feeding_timer()
            self.async_update_listeners()
            try:
                await self._restore_current_intent()
            except Exception:
                self.command_error = "feeding transition unconfirmed; recovery pending"
                if not on:
                    self._feeding_unsub = async_call_later(self.hass, 30, self._feeding_timeout)
                raise
            else:
                await self._save_control(deadline, False)
                self.command_error = None
            finally:
                self.async_update_listeners()

    @callback
    def _feeding_timeout(self, _now) -> None:  # noqa: ANN001
        self._feeding_unsub = None
        if not self._closed:
            self.hass.async_create_task(self.async_feeding_set(False))

    def viewing_target(self) -> list[int]:
        """The per-channel viewing-mode mix (white-heavy, violet damped)."""
        defaults = [90, 50, 60, 25]  # white, blue, color, purple
        return [
            self.viewing_levels.get(
                i, defaults[i] if i < len(defaults) else 40
            )
            for i in range(self.channel_count)
        ]

    def _next_viewing_boundary(self, now):
        """Return a fresh, clock-matched boundary; unsupported data gives no guess."""
        timing, seen = self.schedule_timing, self.schedule_timing_read_at
        if timing is None or seen is None or not 0 <= now - seen <= 90:
            return None
        local = dt_util.as_local(dt_util.utc_from_timestamp(seen))
        # Compare real read header to HA local wall clock, not an assumed timezone.
        year, month, day, hour, minute, second = timing.clock_fields
        device = local.replace(year=2000 + year, month=month, day=day,
                               hour=hour, minute=minute, second=second, microsecond=0)
        skew = device.timestamp() - seen
        if abs(skew) > 90:
            return None
        current = dt_util.as_local(dt_util.utc_from_timestamp(now + skew))
        candidates = []
        for days in (0, 1):
            for boundary in timing.boundaries:
                for fold in (0, 1):
                    value = (current + timedelta(days=days)).replace(
                        hour=boundary // 60, minute=boundary % 60,
                        second=0, microsecond=0, fold=fold)
                    normalized = dt_util.as_local(dt_util.utc_from_timestamp(value.timestamp()))
                    # Skip nonexistent local wall times at a DST transition.
                    if (normalized.date(), normalized.hour, normalized.minute) != (value.date(), value.hour, value.minute):
                        continue
                    deadline = value.timestamp() - skew
                    if deadline > now:
                        candidates.append(deadline)
        return min(candidates) if candidates else None

    def _clear_viewing(self):
        self.viewing_on = False
        self._viewing_started_at = None
        self._viewing_deadline = None
        if self._viewing_unsub is not None:
            self._viewing_unsub()
            self._viewing_unsub = None

    def _arm_viewing_timer(self):
        if self._viewing_unsub is not None:
            self._viewing_unsub()
            self._viewing_unsub = None
        deadline = self._viewing_deadline
        if self.viewing_on and deadline is not None and not self._closed:
            self._viewing_unsub = async_call_later(self.hass, max(0, deadline - time.time()),
                lambda _now: self._viewing_timeout(deadline))

    @callback
    def _viewing_timeout(self, deadline):
        if not self._closed:
            self.hass.async_create_task(self.async_expire_viewing(deadline, timer_elapsed=True))

    async def async_expire_viewing(self, deadline, *, timer_elapsed=False):
        async with self._mode_lock:
            if (self._closed or not self.viewing_on or self._viewing_deadline != deadline
                    or (not timer_elapsed and time.time() < deadline)):
                return
            self._generation += 1
            self._clear_viewing()
            self._manual_channels = None
            if self.feeding_on or self._power_off:
                # Drop only the viewing obligation; never interrupt feeding or relight off.
                await self._save_control(self._feeding_deadline, bool(self.command_error))
                self.async_update_listeners()
            else:
                await self._apply_and_save_control()

    async def _shorten_viewing_deadline(self):
        if not self.viewing_on:
            return
        async with self._mode_lock:
            if self._closed or not self.viewing_on or self._viewing_deadline is None:
                return
            boundary = self._next_viewing_boundary(time.time())
            if boundary is not None and boundary < self._viewing_deadline:
                self._viewing_deadline = boundary
                await self._save_control(self._feeding_deadline, bool(self.command_error))
                self._arm_viewing_timer()

    async def async_viewing_set(self, on: bool) -> None:
        self._generation += 1
        async with self._mode_lock:
            if self._closed:
                raise HomeAssistantError("integration unloaded")
            if on and self._power_off:
                raise HomeAssistantError("turn the light on explicitly before viewing")
            if on and not self.viewing_on:
                now = time.time()
                self._viewing_started_at = now
                self._viewing_deadline = min(now + 1800, self._next_viewing_boundary(now) or now + 1800)
                self.viewing_on = True
            elif not on:
                self._clear_viewing()
            self._arm_viewing_timer()
            await self._apply_and_save_control()

    async def async_set_viewing_level(self, index: int, value: int) -> None:
        self._generation += 1
        async with self._mode_lock:
            if type(value) is not int or not 0 <= value <= self.channel_limit:
                raise HomeAssistantError("viewing outside verified model range")
            self.viewing_levels[index] = value
            if self.viewing_on:
                await self._restore_current_intent()

    async def async_write_schedule(self, slots, start_minute, durations) -> None:
        self._generation += 1
        async with self._mode_lock:
            await self._load_acclimation_base()
            base = [tuple(slot) for slot in slots]
            protocol.build_schedule_times(start_minute, durations)
            protocol.build_schedule_brightness(base)
            scale = self.acclimation_scale
            target = self._scaled_schedule(base, scale)
            pending = {"base": base, "start": start_minute, "durations": durations}
            await self._acclimation_store.async_save({"base": self._acclimation_base,
                "pending_schedule": pending, "scale": scale})
            self._pending_schedule = pending
            await self.client.async_write_schedule(target, start_minute, durations)
            await self._verify_curve(target)
            next_base = base if scale != 100 else None
            await self._acclimation_store.async_save({"base": next_base, "scale": scale})
            self._acclimation_base = next_base
            self._pending_schedule = None
            self.schedule = target
            await self._restore_current_intent()

    @property
    def channel_limit(self):
        return protocol.channel_limit(getattr(self.client, "device_code", protocol.DEFAULT_DEVICE_CODE))

    @property
    def max_schedule_gain(self):
        base = self._acclimation_base if self._acclimation_base is not None else self.schedule
        if not base or len(base) != protocol.NUM_SLOTS or any(len(row) != protocol.NUM_CHANNELS for row in base):
            return 100
        if any(type(v) is not int or not 0 <= v <= self.channel_limit for row in base for v in row):
            return 100
        peak = max(max(row) for row in base)
        return min(200, self.channel_limit * 100 // peak) if peak else 100

    def _scaled_schedule(self, base, value):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 10 <= value <= 200):
            raise HomeAssistantError("schedule gain must be10..200")
        # Validate every baseline channel BEFORE scaling or writing any time field.
        protocol.build_schedule_brightness(base, device_code=getattr(self.client, "device_code", protocol.DEFAULT_DEVICE_CODE))
        peak = max(max(row) for row in base)
        if peak and value > self.channel_limit * 100 // peak:
            raise HomeAssistantError("gain exceeds available channel headroom")
        return [tuple(round(c * value / 100) for c in row) for row in base]

    async def _read_current_curve(self):
        raw = await self.client.async_read_config()
        curve = protocol.parse_schedule_brightness(raw)
        protocol.build_schedule_brightness(curve, device_code=getattr(self.client, "device_code", protocol.DEFAULT_DEVICE_CODE))
        return curve

    async def async_adopt_current_schedule(self, confirmed: bool):
        """Explicitly accept an external edit as100%, without writing to the lamp."""
        if confirmed is not True:
            raise HomeAssistantError("explicit confirmation of current program required")
        async with self._mode_lock:
            await self._load_acclimation_base()
            if self._pending_schedule is not None or self._pending_scale is not None:
                raise HomeAssistantError("resolve pending recovery before adopting an external program")
            current = await self._read_current_curve()
            history = Store(self.hass, 1, self._acclimation_store.key + ".history")
            record = await history.async_load() or {"revisions": []}
            record["revisions"].append({"accepted_at": time.time(), "previous": await self._acclimation_store.async_load(), "accepted_curve": current})
            await history.async_save(record)
            await self._acclimation_store.async_save({"base": None, "scale": 100})
            self._acclimation_base = None
            self.acclimation_scale = 100
            self._acclimation_has_scale = True
            self.schedule_conflict = False
            self.schedule = current
            self.async_update_listeners()

    async def async_apply_acclimation(self, value: int) -> None:
        self._generation += 1
        async with self._mode_lock:
            await self._load_acclimation_base()
            if self._pending_schedule is not None:
                raise HomeAssistantError("retry the pending schedule before changing dimming")
            current = await self._read_current_curve()
            if self._acclimation_base is None:
                if self.acclimation_scale != 100:
                    raise HomeAssistantError("missing100% baseline; explicitly adopt the current program")
                self._acclimation_base = [tuple(slot) for slot in current]
            base = self._acclimation_base
            old_target = self._scaled_schedule(base, self.acclimation_scale)
            permitted = [old_target]
            if self._pending_scale is not None:
                if value != self._pending_scale:
                    raise HomeAssistantError("retry pending gain before selecting another value")
                permitted.append(self._scaled_schedule(base, self._pending_scale))
            if current not in permitted:
                self.schedule_conflict = True
                self.schedule = current
                self.async_update_listeners()
                raise HomeAssistantError("external schedule change: refusing to overwrite; explicitly adopt current program")
            target = self._scaled_schedule(base, value)
            await self._acclimation_store.async_save({"base": base,
                "scale": self.acclimation_scale, "pending_scale": value})
            self._pending_scale = value
            await self.client.async_write_brightness(target)
            await self._verify_curve(target)
            next_base = None if value == 100 else base
            await self._acclimation_store.async_save({"base": next_base, "scale": value})
            self._acclimation_base = next_base
            self.acclimation_scale = value
            self._pending_scale = None
            self.schedule_conflict = False
            self.schedule = target
            await self._restore_current_intent()

    async def _load_acclimation_base(self) -> None:
        if self._acclimation_loaded:
            return
        data = await self._acclimation_store.async_load()
        if data:
            self._acclimation_base = [tuple(s) for s in data["base"]] if data.get("base") else None
            self._pending_schedule = data.get("pending_schedule")
            self._pending_scale = data.get("pending_scale")
            if "scale" in data:
                scale = data["scale"]
                if type(scale) is not int or not 10 <= scale <= 200:
                    raise HomeAssistantError("invalid saved dimming scale; recovery required")
                self.acclimation_scale = scale
                self._acclimation_has_scale = True
        self._acclimation_loaded = True

    async def async_read_config(self) -> bytes:
        """Read the raw 0x10 config reply and cache it."""
        self.last_config = await self.client.async_read_config()
        return self.last_config


    @property
    def active_mode(self):
        if self._power_off: return "off"
        if self.feeding_on: return "feeding"
        if self.viewing_on: return "viewing"
        if self._manual_channels is not None: return "manual"
        return "schedule"

    async def _restore_current_intent(self):
        if self._closed:
            return
        mode = self.active_mode
        if mode == "off":
            await self.client.async_turn_off()
        elif mode == "schedule":
            await self._resume_program()
        else:
            self.channels = ([self.feeding_level] * self.channel_count if mode == "feeding"
                             else self.viewing_target() if mode == "viewing" else list(self._manual_channels))
            fade = await self._fade_suspend()
            try:
                await self.async_apply_channels()
            finally:
                await self._fade_resume(fade)
        self.async_update_listeners()

    async def async_user_off(self):
        self._generation += 1
        async with self._mode_lock:
            self._power_off = True
            self._clear_viewing()
            await self._apply_and_save_control()

    async def async_resume_schedule(self):
        """Explicitly drop preview, preserving higher-priority active modes."""
        self._generation += 1
        async with self._mode_lock:
            self._power_off = False
            self._manual_channels = None
            self._clear_viewing()
            await self._apply_and_save_control()

    async def _apply_and_save_control(self):
        try:
            await self._save_control(self._feeding_deadline, True)
            await self._restore_current_intent()
        except (Exception, asyncio.CancelledError):
            self.command_error = "lighting transition unconfirmed; recovery pending"
            if self._control_retry_unsub is None:
                self._control_retry_unsub = async_call_later(self.hass, 30, self._control_retry_timeout)
            raise
        else:
            await self._save_control(self._feeding_deadline, False)
            self.command_error = None
            if self._control_retry_unsub is not None:
                self._control_retry_unsub()
                self._control_retry_unsub = None

    @callback
    def _control_retry_timeout(self, _now):
        self._control_retry_unsub = None
        if not self._closed:
            self.hass.async_create_task(self._async_retry_current_intent())

    async def _async_retry_current_intent(self):
        async with self._mode_lock:
            if self._closed:
                return
            self._generation += 1
            # Retry what is wanted now, never cancel a subsequently started feed.
            await self._apply_and_save_control()

    async def _save_control(self, deadline, pending):
        await self._feeding_store.async_save({"deadline": deadline,
            "recovery_pending": pending, "level": self.feeding_level,
            "power_off": self._power_off, "viewing": self.viewing_on,
            "viewing_started_at": self._viewing_started_at,
            "viewing_deadline": self._viewing_deadline,
            "manual_channels": self._manual_channels})

    def _arm_feeding_timer(self):
        if self._feeding_unsub is not None:
            self._feeding_unsub()
            self._feeding_unsub = None
        if self._feeding_deadline is not None:
            self._feeding_unsub = async_call_later(self.hass,
                max(0, self._feeding_deadline - time.time()), self._feeding_timeout)

    async def async_restore_feeding(self):
        saved = await self._feeding_store.async_load()
        if not saved:
            return
        self._power_off = bool(saved.get("power_off", False))
        self.viewing_on = bool(saved.get("viewing", False))
        self._manual_channels = saved.get("manual_channels")
        self._feeding_deadline = saved.get("deadline")
        self.feeding_level = saved.get("level", self.feeding_level)
        if self._feeding_deadline is not None:
            # Keep the real deadline, even if it expires while HA is starting.
            self.feeding_on = True
            self._arm_feeding_timer()
        view_dropped = False
        if self.viewing_on:
            start, deadline, now = saved.get("viewing_started_at"), saved.get("viewing_deadline"), time.time()
            valid = (all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                         for v in (start, deadline)) and start <= now < deadline <= start + 1800)
            if self._power_off or not valid:
                # Includes legacy unbounded viewing, missed expiry and backward-clock jumps.
                self._clear_viewing()
                self._manual_channels = None
                view_dropped = True
            else:
                self._viewing_started_at, self._viewing_deadline = start, deadline
                self._arm_viewing_timer()
        if view_dropped and not self.feeding_on:
            await self._apply_and_save_control()
        elif view_dropped:
            await self._save_control(self._feeding_deadline, bool(saved.get("recovery_pending")))
        elif saved.get("recovery_pending") and self._feeding_deadline is None:
            await self.async_feeding_set(False)

    async def async_shutdown(self):
        self._closed = True
        self._generation += 1
        if self._control_retry_unsub is not None:
            self._control_retry_unsub()
            self._control_retry_unsub = None
        if self._viewing_unsub is not None:
            self._viewing_unsub()
            self._viewing_unsub = None
        if self._feeding_unsub is not None:
            self._feeding_unsub()
            self._feeding_unsub = None

    async def _verify_curve(self, target):
        raw = await self.client.async_read_config()
        observed = protocol.parse_schedule_brightness(raw)
        if observed != target:
            self.command_error = "schedule write unconfirmed; original and pending target retained"
            raise HomeAssistantError(self.command_error)
        self.command_error = None

    async def _begin_effect(self, generation):
        async with self._mode_lock:
            if self._closed or generation != self._generation:
                raise _EffectInterrupted()
            try:
                fade = await self.client.async_read_options()
            except (ZetlightUDPError, ValueError):
                return None
            if generation != self._generation:
                raise _EffectInterrupted()
            if fade.fade_enable:
                await self.client.async_set_fade(False, fade.fade_minutes)
            return fade

    async def _effect_set_brightness(self, values, generation):
        async with self._mode_lock:
            if self._closed or generation != self._generation:
                raise _EffectInterrupted()
            await self.client.async_set_brightness(values)

    async def _finish_effect(self, generation, fade, fade_generation):
        async with self._mode_lock:
            if self._closed:
                return
            if fade_generation == self._fade_generation:
                await self._fade_resume(fade)
            if generation == self._generation:
                await self._restore_current_intent()


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

    try:
        await coordinator.async_restore_feeding()
    except (ZetlightUDPError, HomeAssistantError) as err:
        await coordinator.async_shutdown()
        client.close()
        raise ConfigEntryNotReady("pending lighting recovery could not finish") from err
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
SERVICE_ADOPT_SCHEDULE = "adopt_current_schedule"

_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_ids"): vol.All(cv.ensure_list, [cv.string]),
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
    if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
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
    if any(not 0 <= duration <= 1439 for duration in durations):
        raise HomeAssistantError("slot duration out of range")
    if any(not 0 <= value <= 200 for slot in slots for value in slot):
        raise HomeAssistantError("preset brightness must be 0-200")
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

    def selected(call):
        available = {entry.entry_id: entry.runtime_data for entry in
                     hass.config_entries.async_entries(DOMAIN)
                     if entry.state is ConfigEntryState.LOADED}
        ids = call.data.get("entry_ids")
        if ids is None:
            if len(available) != 1:
                raise HomeAssistantError("select explicit entry_ids when zero or multiple lights are loaded")
            return list(available.values())
        if not ids or any(key not in available for key in ids):
            raise HomeAssistantError("every selected entry_id must be a loaded Zetlight light")
        return [available[key] for key in dict.fromkeys(ids)]

    async def handle_set_schedule(call: ServiceCall) -> None:
        start = _parse_hhmm(call.data["start"])
        durations = list(call.data["durations"])
        slots = [tuple(slot) for slot in call.data["brightness"]]
        coordinators = selected(call)
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

    async def handle_adopt_schedule(call: ServiceCall) -> None:
        for coordinator in selected(call):
            await coordinator.async_adopt_current_schedule(call.data["confirm_current"])

    hass.services.async_register(DOMAIN, SERVICE_ADOPT_SCHEDULE, handle_adopt_schedule,
        schema=vol.Schema({vol.Optional("entry_ids"): vol.All(cv.ensure_list, [cv.string]),
                           vol.Required("confirm_current"): vol.In([True])}))
    hass.services.async_register(
        DOMAIN, SERVICE_SET_SCHEDULE, handle_set_schedule, schema=_SET_SCHEDULE_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_SYNC_CLOCK, handle_sync_clock)


async def async_unload_entry(hass: HomeAssistant, entry: ZetlightConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
        entry.runtime_data.client.close()
        # Drop the shared services once the last entry is gone.
        loaded = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.state.recoverable
        ]
        if not loaded:
            for service in (SERVICE_SET_SCHEDULE, SERVICE_SYNC_CLOCK, SERVICE_ADOPT_SCHEDULE):
                hass.services.async_remove(DOMAIN, service)
    return unload_ok
