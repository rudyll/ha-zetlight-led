"""Per-channel brightness controls (A/B/C/D) for the Zetlight Horizon Aqua LED."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZetlightConfigEntry, ZetlightCoordinator
from .const import (
    DOMAIN,
    FEEDING_DEFAULT_LEVEL,
    FEEDING_DEFAULT_MINUTES,
    LIGHTNING_DEFAULT_FLASHES,
    LIGHTNING_DEFAULT_INTENSITY,
    LIGHTNING_DEFAULT_ON_MS,
)
from .protocol import NUM_CHANNELS

# App labels the four channels A/B/C/D.
CHANNEL_LABELS = ("A", "B", "C", "D")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZetlightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-channel sliders and the lightning config numbers."""
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = [
        ZetlightChannelNumber(coordinator, entry.entry_id, index)
        for index in range(NUM_CHANNELS)
    ]
    entities.extend(
        [
            ZetlightLightningParam(
                coordinator, entry.entry_id, "lightning_flashes",
                "Lightning flashes", 1, 5, 1, None, LIGHTNING_DEFAULT_FLASHES,
                "mdi:flash",
            ),
            ZetlightLightningParam(
                coordinator, entry.entry_id, "lightning_intensity",
                "Lightning intensity", 10, 100, 1, PERCENTAGE,
                LIGHTNING_DEFAULT_INTENSITY, "mdi:brightness-percent",
            ),
            ZetlightLightningParam(
                coordinator, entry.entry_id, "lightning_on_ms",
                "Lightning flash duration", 30, 300, 10,
                UnitOfTime.MILLISECONDS, LIGHTNING_DEFAULT_ON_MS, "mdi:timer-outline",
            ),
            ZetlightLightningParam(
                coordinator, entry.entry_id, "feeding_level",
                "Feeding level", 0, 100, 1, PERCENTAGE,
                FEEDING_DEFAULT_LEVEL, "mdi:brightness-5",
            ),
            ZetlightLightningParam(
                coordinator, entry.entry_id, "feeding_minutes",
                "Feeding duration", 1, 120, 1, UnitOfTime.MINUTES,
                FEEDING_DEFAULT_MINUTES, "mdi:timer-sand",
            ),
            ZetlightLightningParam(
                coordinator, entry.entry_id, "acclimation_scale",
                "Acclimation", 10, 100, 1, PERCENTAGE, 100, "mdi:sprout",
            ),
        ]
    )
    async_add_entities(entities)


class ZetlightChannelNumber(CoordinatorEntity[ZetlightCoordinator], NumberEntity):
    """A single channel's brightness (0-100%), applied live via 0x13.

    All four channels share the coordinator's channel state; setting one sends
    a full 0x13 frame with the other channels left at their current values.
    This is a real-time preview and does not persist to the device's stored
    program. Values are OPTIMISTIC apart from the initial seed from the device's
    reported setpoints (see the coordinator).
    """

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:led-strip-variant"

    def __init__(
        self, coordinator: ZetlightCoordinator, entry_id: str, index: int
    ) -> None:
        super().__init__(coordinator)
        self._index = index
        label = CHANNEL_LABELS[index]
        self._attr_translation_key = f"channel_{label.lower()}"
        self._attr_unique_id = f"{entry_id}_channel_{label.lower()}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float:
        return self.coordinator.channels[self._index]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_channel(self._index, int(value))


class ZetlightLightningParam(CoordinatorEntity[ZetlightCoordinator], RestoreNumber):
    """A tunable local config number (lightning or feeding parameters).

    Pure local config (no device I/O): the value is stored on the coordinator
    and read by the lightning button / feeding switch. Restored across restarts.
    """

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: ZetlightCoordinator,
        entry_id: str,
        attr: str,
        name: str,
        minimum: float,
        maximum: float,
        step: float,
        unit: str | None,
        default: int,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = attr  # `name` kept for readability only
        self._attr_unique_id = f"{entry_id}_{attr}"
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})
        self._coord_attr = attr
        self._value: float = float(default)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self._value = last.native_value
        setattr(self.coordinator, self._coord_attr, int(self._value))

    @property
    def native_value(self) -> float:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        setattr(self.coordinator, self._coord_attr, int(value))
        self.async_write_ha_state()
