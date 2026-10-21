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
    """Set up the schedule sensor."""
    async_add_entities([ZetlightScheduleSensor(entry.runtime_data, entry.entry_id)])


class ZetlightScheduleSensor(CoordinatorEntity[ZetlightCoordinator], SensorEntity):
    """Read-only view of the stored per-slot brightness schedule.

    State is the peak brightness across all slots/channels; the full 5-slot x
    4-channel curve (raw %, decoded from the 0x10 reply) is in the attributes.
    Times are not decoded yet, so only brightness is shown.
    """

    _attr_has_entity_name = True
    _attr_name = "Schedule"
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
    def extra_state_attributes(self) -> dict[str, list[int]] | None:
        schedule = self.coordinator.schedule
        if not schedule:
            return None
        attrs = {"channels": list(CHANNEL_LABELS)}
        for i, slot in enumerate(schedule, start=1):
            attrs[f"slot_{i}"] = list(slot)
        return attrs
