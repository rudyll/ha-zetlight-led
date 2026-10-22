"""Switch platform: feeding / maintenance mode."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up the feeding-mode and native coral-acclimation switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ZetlightFeedingSwitch(coordinator, entry.entry_id),
            ZetlightCoralSwitch(coordinator, entry.entry_id),
        ]
    )


class ZetlightFeedingSwitch(CoordinatorEntity[ZetlightCoordinator], SwitchEntity):
    """Feeding / maintenance mode: dim all channels, auto-restore on timeout.

    Turning on dims every channel to the configured feeding level and starts a
    timer; it restores the previous levels when the timer elapses or when turned
    off. Uses live 0x13 frames; the stored program is untouched.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "feeding_mode"
    _attr_icon = "mdi:food-apple"

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_feeding"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool:
        return self.coordinator.feeding_on

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_feeding_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_feeding_set(False)


class ZetlightCoralSwitch(CoordinatorEntity[ZetlightCoordinator], SwitchEntity):
    """The device's native coral-acclimation mode (0x14).

    Device-managed: the lamp ramps its own output up over several days without
    changing your stored schedule. Non-destructive — unlike the `Acclimation`
    number, this is the vendor's built-in mode, and `sensor.acclimation_day`
    shows its progress.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "coral_acclimation"
    _attr_icon = "mdi:sprout-outline"

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_coral_acclimation"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool | None:
        opts = self.coordinator.options
        if opts is None:
            return None
        return opts.coral > 0

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_coral(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_coral(False)
