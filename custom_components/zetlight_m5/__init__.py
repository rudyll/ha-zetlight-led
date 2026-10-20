"""Zetlight M5 coral light — local UDP integration for Home Assistant.

Pure local control: binds a UDP socket, sends ``EE...CC`` request frames to the
device on port 8855 and parses ``DD...CC`` replies. No cloud, no Bluetooth.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import protocol
from .const import (
    CONF_DEVICE_CODE,
    DEFAULT_PORT,
    DOMAIN,
    REQUEST_TIMEOUT,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.NUMBER]


class ZetlightUDPError(Exception):
    """Raised when a UDP request fails or times out."""


class _ClientProtocol(asyncio.DatagramProtocol):
    """Minimal datagram protocol that resolves one pending reply at a time."""

    def __init__(self) -> None:
        self._pending: asyncio.Future[bytes] | None = None

    def set_pending(self, future: asyncio.Future[bytes]) -> None:
        self._pending = future

    def datagram_received(self, data: bytes, addr) -> None:  # noqa: ANN001
        if self._pending is not None and not self._pending.done():
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

    async def _request(self, frame: bytes, *, expect_reply: bool) -> bytes | None:
        if self._transport is None or self._proto is None:
            raise ZetlightUDPError("client not connected")
        async with self._lock:
            loop = asyncio.get_running_loop()
            future: asyncio.Future[bytes] = loop.create_future()
            self._proto.set_pending(future)
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
        reply = await self._request(frame, expect_reply=True)
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


type ZetlightConfigEntry = ConfigEntry[ZetlightCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ZetlightConfigEntry) -> bool:
    """Set up a Zetlight M5 device from a config entry."""
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZetlightConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.client.close()
    return unload_ok
