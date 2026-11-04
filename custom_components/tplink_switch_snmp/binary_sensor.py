"""Link state of every port."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SwitchConfigEntry, SwitchCoordinator
from .entity import PortEntity
from .selection import wants

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a link sensor per port."""
    coordinator = entry.runtime_data
    async_add_entities(
        PortLink(coordinator, n) for n in coordinator.data.ports if wants(entry, n, "link")
    )


class PortLink(PortEntity, BinarySensorEntity):
    """Whether a cable with a live partner is connected."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "link"

    def __init__(self, coordinator: SwitchCoordinator, number: int) -> None:
        super().__init__(coordinator, number, "link")

    @property
    def is_on(self) -> bool | None:
        return self.port.up if self.port else None
