"""Switch platform: feeding / maintenance mode."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
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
            ZetlightAutoCloudSwitch(coordinator, entry.entry_id),
            ZetlightMoonSwitch(coordinator, entry.entry_id),
            ZetlightFadeSwitch(coordinator, entry.entry_id),
            ZetlightViewingSwitch(coordinator, entry.entry_id),
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


class ZetlightAutoCloudSwitch(CoordinatorEntity[ZetlightCoordinator], SwitchEntity):
    """Auto-clouds: the device randomly dims briefly during the day (0x14)."""

    _attr_has_entity_name = True
    _attr_translation_key = "auto_cloud"
    _attr_icon = "mdi:weather-cloudy"

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_auto_cloud"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool | None:
        opts = self.coordinator.options
        return None if opts is None else opts.auto_cloud > 0

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_auto_cloud(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_auto_cloud(False)


class ZetlightMoonSwitch(CoordinatorEntity[ZetlightCoordinator], SwitchEntity):
    """Moon-phase mode: moonlight follows the lunar cycle at night (0x19)."""

    _attr_has_entity_name = True
    _attr_translation_key = "moon_phase"
    _attr_icon = "mdi:moon-waning-crescent"

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_moon_phase"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool | None:
        opts = self.coordinator.options
        return None if opts is None else opts.moon > 0

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_moon(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_moon(False)


class ZetlightFadeSwitch(CoordinatorEntity[ZetlightCoordinator], SwitchEntity):
    """Gradient/fade: smooth transitions between brightness changes (0x22).

    Keep it on for smooth schedule transitions; the lightning effect turns it
    off by itself for the duration of a strike so flashes stay sharp.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "fade"
    _attr_icon = "mdi:transition"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_fade"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    def _minutes(self) -> int:
        opts = self.coordinator.options
        return opts.fade_minutes if opts and opts.fade_minutes else 3

    @property
    def is_on(self) -> bool | None:
        opts = self.coordinator.options
        return None if opts is None else opts.fade_enable > 0

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_fade(True, self._minutes())

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_fade(False, self._minutes())


class ZetlightViewingSwitch(CoordinatorEntity[ZetlightCoordinator], SwitchEntity):
    """Viewing / photo mode: a white-balanced mix that is easy on the eye and the
    camera while corals still fluoresce.

    More white, moderate blue (keeps fluorescence), damped violet (the most
    camera-polluting). Live-only; restores the previous levels when switched off,
    and stays on until you turn it off. Tune the per-channel targets with the
    'Viewing …' config numbers.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "viewing_mode"
    _attr_icon = "mdi:camera-iris"

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_viewing_mode"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool:
        return self.coordinator.viewing_on

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_viewing_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_viewing_set(False)
