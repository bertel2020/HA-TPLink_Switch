"""Link state of every port."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FEATURES
from .coordinator import SwitchConfigEntry, SwitchCoordinator
from .entity import PortEntity, SwitchEntity
from .selection import selected_groups, wants

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
    # the functions of the switch that are on or off as a whole, where the switch tells
    groups = selected_groups(entry)
    entities.extend(
        SwitchFeature(coordinator, name)
        for name, (group, _) in FEATURES.items()
        if group in groups and name in coordinator.data.features
    )
    async_add_entities(entities)


class SwitchFeature(SwitchEntity, BinarySensorEntity):
    """Whether a function of the switch (DoS defence, DHCP snooping, 802.1X ...) is switched on."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SwitchCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._name = name
        self._attr_translation_key = f"feature_{name}"
        self._attr_unique_id = f"{self._mac}_feature_{name}"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.features.get(self._name)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """For port mirroring: the groups that are on, with the monitor port and the sources."""
        if self._name == "mirror":
            return {"groups": self.coordinator.data.mirror}
        return None


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
