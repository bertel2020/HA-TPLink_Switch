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
    ports = coordinator.data.ports
    entities: list[BinarySensorEntity] = [
        PortLink(coordinator, n) for n in ports if wants(entry, n, "link")
    ]
    # only for ports the switch watches for loops
    entities.extend(
        PortLoop(coordinator, n)
        for n, port in ports.items()
        if port.loop is not None and wants(entry, n, "loop")
    )
    async_add_entities(entities)


class PortLink(PortEntity, BinarySensorEntity):
    """Whether a cable with a live partner is connected."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "link"

    def __init__(self, coordinator: SwitchCoordinator, number: int) -> None:
        super().__init__(coordinator, number, "link")

    @property
    def is_on(self) -> bool | None:
        return self.port.up if self.port else None


class PortLoop(PortEntity, BinarySensorEntity):
    """Whether the switch has found a loop at the port."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "loop"

    def __init__(self, coordinator: SwitchCoordinator, number: int) -> None:
        super().__init__(coordinator, number, "loop")

    @property
    def is_on(self) -> bool | None:
        return self.port.loop if self.port else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Besides the port: whether the switch has blocked it."""
        blocked = self.port.loop_blocked if self.port else None
        return {**super().extra_state_attributes, "blocked": blocked}
