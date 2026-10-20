"""Light platform for the Zetlight M5 coral light."""

from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZetlightConfigEntry, ZetlightCoordinator
from .const import DOMAIN
from .protocol import NUM_CHANNELS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZetlightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light entity for a config entry."""
    async_add_entities([ZetlightLight(entry.runtime_data, entry.entry_id)])


def _ha_to_device(brightness: int) -> int:
    """Map Home Assistant brightness (0-255) to a device level (1-100)."""
    return max(1, min(100, round(brightness / 255 * 100)))


class ZetlightLight(CoordinatorEntity[ZetlightCoordinator], LightEntity):
    """On/off + brightness control for the M5 coral light.

    Brightness is applied to all four channels together as a single overall
    level via the device-verified 0x13 command (see protocol.build_brightness).
    Per-channel control is possible with the same frame but is not exposed here.

    Note: 0x13 is a real-time preview — it sets the live output but does not
    write the device's stored time-curve program.

    ``is_on`` and ``brightness`` are OPTIMISTIC. The 0x0C read command returns
    per-channel *setpoints*, which do not change when the lamp is switched off,
    so there is no reliable way to read back the current on/off state. We track
    the last command we sent and assume it took effect.
    """

    _attr_has_entity_name = True
    _attr_name = None  # use the device name
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry_id
        self._is_on: bool | None = None
        self._brightness: int | None = None
        code = coordinator.client.device_code.hex().upper()
        name = coordinator.data.name if coordinator.data else "Zetlight M5"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer="Zetlight",
            model="M5-80M",
            name=name or "Zetlight M5",
            serial_number=code,
        )

    @property
    def is_on(self) -> bool | None:
        """Optimistic on/off state; None until a command is sent."""
        return self._is_on

    @property
    def brightness(self) -> int | None:
        """Optimistic brightness (0-255); None until a level is set."""
        return self._brightness

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            level = _ha_to_device(brightness)
            channels = (level,) * NUM_CHANNELS
            await self.coordinator.client.async_set_brightness(channels)
            self._brightness = brightness
        else:
            # No brightness requested: resume the device's stored program.
            await self.coordinator.client.async_turn_on()
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.async_turn_off()
        self._is_on = False
        self.async_write_ha_state()
