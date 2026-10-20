"""Per-channel brightness controls (A/B/C/D) for the Zetlight Horizon Aqua LED."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZetlightConfigEntry, ZetlightCoordinator
from .const import DOMAIN
from .protocol import NUM_CHANNELS

# App labels the four channels A/B/C/D.
CHANNEL_LABELS = ("A", "B", "C", "D")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZetlightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one number entity per channel."""
    coordinator = entry.runtime_data
    async_add_entities(
        ZetlightChannelNumber(coordinator, entry.entry_id, index)
        for index in range(NUM_CHANNELS)
    )


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
        self._attr_name = f"Channel {label}"
        self._attr_unique_id = f"{entry_id}_channel_{label.lower()}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float:
        return self.coordinator.channels[self._index]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_channel(self._index, int(value))
