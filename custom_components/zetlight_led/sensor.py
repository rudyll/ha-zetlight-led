"""Sensor platform: exposes the device's stored daily schedule (read-only)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZetlightConfigEntry, ZetlightCoordinator
from .const import DOMAIN
from .number import CHANNEL_LABELS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZetlightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the schedule sensor and the per-channel raw-value sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        ZetlightScheduleSensor(coordinator, entry.entry_id)
    ]
    entities.extend(
        ZetlightRawChannelSensor(coordinator, entry.entry_id, i)
        for i in range(coordinator.channel_count)
    )
    entities.append(ZetlightAcclimationDaySensor(coordinator, entry.entry_id))
    async_add_entities(entities)


class ZetlightScheduleSensor(CoordinatorEntity[ZetlightCoordinator], SensorEntity):
    """Read-only view of the stored per-slot brightness schedule.

    State is the peak brightness across all slots/channels; the full 5-slot x
    4-channel curve (raw %, decoded from the 0x10 reply) is in the attributes.
    Times are not decoded yet, so only brightness is shown.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "schedule"
    _attr_icon = "mdi:chart-timeline-variant"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_schedule"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> int | None:
        schedule = self.coordinator.schedule
        if not schedule:
            return None
        return max(max(slot) for slot in schedule)

    @property
    def extra_state_attributes(self) -> dict | None:
        schedule = self.coordinator.schedule
        if not schedule:
            return None
        attrs = {"channels": list(CHANNEL_LABELS)}
        timing = self.coordinator.schedule_timing
        attrs["schedule_boundary_minutes"] = list(timing.boundaries) if timing else None
        attrs["schedule_timing_read_at_unix"] = self.coordinator.schedule_timing_read_at
        for i, slot in enumerate(schedule, start=1):
            attrs[f"slot_{i}"] = list(slot)
        return attrs


class ZetlightRawChannelSensor(CoordinatorEntity[ZetlightCoordinator], SensorEntity):
    """A single channel's raw drive value from the 0x0C status reply.

    These are the device's internal per-channel values (diagnostic); their exact
    unit/scale is not documented, so no unit is attached.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:sine-wave"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: ZetlightCoordinator, entry_id: str, index: int
    ) -> None:
        super().__init__(coordinator)
        self._index = index
        label = CHANNEL_LABELS[index]
        self._attr_translation_key = f"channel_{label.lower()}_raw"
        self._attr_unique_id = f"{entry_id}_channel_{label.lower()}_raw"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        if data is None or self._index >= len(data.raw):
            return None
        return data.raw[self._index]


class ZetlightAcclimationDaySensor(
    CoordinatorEntity[ZetlightCoordinator], SensorEntity
):
    """Native coral-acclimation progress (day 1-10; 0 = not running)."""

    _attr_has_entity_name = True
    _attr_translation_key = "acclimation_day"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_acclimation_day"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> int | None:
        opts = self.coordinator.options
        return None if opts is None else opts.coral
