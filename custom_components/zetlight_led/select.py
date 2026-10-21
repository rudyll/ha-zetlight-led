"""Select platform: apply a named schedule preset."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZetlightConfigEntry, ZetlightCoordinator, preset_to_args
from .const import CONF_PRESETS, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZetlightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the preset select entity (only if presets are configured)."""
    presets = dict(entry.options.get(CONF_PRESETS, {}) or {})
    if presets:
        async_add_entities(
            [ZetlightPresetSelect(entry.runtime_data, entry.entry_id, presets)]
        )


class ZetlightPresetSelect(CoordinatorEntity[ZetlightCoordinator], SelectEntity):
    """Apply one of the user's named schedule presets (write via set_schedule).

    Selecting a preset overwrites the device's stored program. The current
    option is optimistic (the last preset applied this session).
    """

    _attr_has_entity_name = True
    _attr_translation_key = "preset"
    _attr_icon = "mdi:playlist-check"

    def __init__(
        self, coordinator: ZetlightCoordinator, entry_id: str, presets: dict
    ) -> None:
        super().__init__(coordinator)
        self._presets = presets
        self._attr_unique_id = f"{entry_id}_preset"
        self._attr_options = sorted(presets.keys())
        self._attr_current_option = None
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    async def async_select_option(self, option: str) -> None:
        preset = self._presets.get(option)
        if preset is None:
            raise HomeAssistantError(f"unknown preset: {option}")
        slots, start, durations = preset_to_args(preset)
        await self.coordinator.async_write_schedule(slots, start, durations)
        self._attr_current_option = option
        self.async_write_ha_state()
