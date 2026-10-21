"""Zetlight Horizon Aqua LED — local UDP integration for Home Assistant.

Pure local control: binds a UDP socket, sends ``EE...CC`` request frames to the
device on port 8855 and parses ``DD...CC`` replies. No cloud, no Bluetooth.
"""

from __future__ import annotations

import asyncio
import logging
import random

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import protocol
from .const import (
    CONF_DEVICE_CODE,
    DEFAULT_PORT,
    DOMAIN,
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
]


class ZetlightUDPError(Exception):
    """Raised when a UDP request fails or times out."""


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

    async def async_read_config(self) -> bytes:
        """Send 0x10 and return the raw reply (schedule config)."""
        reply = await self._request(
            protocol.build_read_config(device_code=self.device_code),
            expect_reply=True,
            expect_cmd=protocol.CMD_READ_CONFIG,
        )
        assert reply is not None
        return reply

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

    def __init__(self, hass: HomeAssistant, client: ZetlightClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self.channels: list[int] = [0] * protocol.NUM_CHANNELS
        self._channels_seeded = False
        # Tunable custom-lightning parameters (set by number entities).
        self.lightning_flashes = LIGHTNING_DEFAULT_FLASHES
        self.lightning_intensity = LIGHTNING_DEFAULT_INTENSITY
        self.lightning_on_ms = LIGHTNING_DEFAULT_ON_MS
        self._lightning_lock = asyncio.Lock()
        # Raw bytes of the last 0x10 config reply (for schedule decoding work).
        self.last_config: bytes | None = None
        # Parsed per-slot brightness from the last 0x10 reply (raw %), or None.
        self.schedule: list[tuple[int, int, int, int]] | None = None

    async def _async_update_data(self) -> protocol.DeviceStatus:
        try:
            status = await self.client.async_read_status()
        except ZetlightUDPError as err:
            raise UpdateFailed(str(err)) from err
        # Seed the channel state once from the device's reported setpoints so
        # the sliders start at sensible values. These are the current program
        # setpoints, not live on/off state (see docs §6).
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
        return status

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
        self.channels = [max(0, min(100, level))] * protocol.NUM_CHANNELS
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
            count = max(1, int(self.lightning_flashes))
            peak = max(1, min(100, int(self.lightning_intensity)))
            on_s = max(0.02, int(self.lightning_on_ms) / 1000)
            try:
                for n in range(count):
                    # white + blue bright, color + purple off
                    await self.client.async_set_brightness((peak, peak, 0, 0))
                    await asyncio.sleep(on_s * random.uniform(0.8, 1.0))
                    if n < count - 1:
                        await self.client.async_set_brightness((0, 0, 0, 0))
                        await asyncio.sleep(random.uniform(0.03, 0.12))
            finally:
                # restore the integration's last known levels
                await self.client.async_set_brightness(saved)

    async def async_write_schedule(
        self,
        slots: list[tuple[int, int, int, int]],
        start_minute: int,
        durations: list[int],
    ) -> None:
        """Write the daily schedule to the device (overwrites stored program)."""
        await self.client.async_write_schedule(slots, start_minute, durations)

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

    coordinator = ZetlightCoordinator(hass, client)
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
    return True


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
                    [vol.All(vol.Coerce(int), vol.Range(min=0, max=100))],
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
