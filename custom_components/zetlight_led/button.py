"""Button platform for the Zetlight Horizon Aqua LED."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ZetlightConfigEntry, ZetlightCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZetlightConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ZetlightLightningButton(coordinator, entry.entry_id),
            ZetlightSyncClockButton(coordinator, entry.entry_id),
            ZetlightReadConfigButton(coordinator, entry.entry_id),
        ]
    )


class _ZetlightButton(CoordinatorEntity[ZetlightCoordinator], ButtonEntity):
    """Base for Zetlight buttons (shares device info)."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ZetlightCoordinator, entry_id: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})


class ZetlightLightningButton(_ZetlightButton):
    """Trigger a custom lightning flash (white+blue, no purple afterglow)."""

    _attr_name = "Lightning"
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "lightning")

    async def async_press(self) -> None:
        await self.coordinator.async_lightning()


class ZetlightSyncClockButton(_ZetlightButton):
    """Sync the device clock to Home Assistant's local time."""

    _attr_name = "Sync clock"
    _attr_icon = "mdi:clock-check"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "sync_clock")

    async def async_press(self) -> None:
        await self.coordinator.client.async_sync_time(dt_util.now())


class ZetlightReadConfigButton(_ZetlightButton):
    """Read the raw 0x10 config reply (for schedule decoding work)."""

    _attr_name = "Read config"
    _attr_icon = "mdi:download"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ZetlightCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "read_config")

    async def async_press(self) -> None:
        raw = await self.coordinator.async_read_config()
        _LOGGER.info("Zetlight 0x10 config reply: %s", raw.hex().upper())
