"""Light platform for the Zetlight M5 coral light."""

from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZetlightConfigEntry, ZetlightCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZetlightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light entity for a config entry."""
    async_add_entities([ZetlightLight(entry.runtime_data, entry.entry_id)])


class ZetlightLight(CoordinatorEntity[ZetlightCoordinator], LightEntity):
    """On/off control for the M5 coral light.

    Brightness is intentionally NOT exposed yet: the 0x13 dimming payload still
    has unconfirmed ``i``/``i6`` bytes (see protocol.build_set_light), so the
    only safe, device-verified controls are ON (0x1E) and OFF (0x1F).

    ``is_on`` is OPTIMISTIC. The 0x0C read command returns per-channel
    *setpoints*, which do not change when the lamp is switched off, so there is
    no reliable way to read back the current on/off state. We therefore track
    the last command we sent and assume it took effect.
    """

    _attr_has_entity_name = True
    _attr_name = None  # use the device name
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry_id
        self._is_on: bool | None = None
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

    async def async_turn_on(self, **kwargs) -> None:
        # TODO: once 0x13 i/i6 are confirmed, honour kwargs[ATTR_BRIGHTNESS]
        # here and add ColorMode.BRIGHTNESS to _attr_supported_color_modes.
        await self.coordinator.client.async_turn_on()
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.async_turn_off()
        self._is_on = False
        self.async_write_ha_state()
