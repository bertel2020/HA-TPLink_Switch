"""Switch a port on or off, when writing to the switch is allowed in the options."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity as HomeAssistantSwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SwitchConfigEntry, SwitchCoordinator
from .entity import PortEntity

PARALLEL_UPDATES = 1  # one write at a time


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a switch per port, but only if the options allow writing."""
    coordinator = entry.runtime_data
    if not coordinator.can_write:
        return
    async_add_entities(PortEnabled(coordinator, number) for number in coordinator.data.ports)


class PortEnabled(PortEntity, HomeAssistantSwitchEntity):
    """The administrative state of a port: off means no link, whatever is plugged in."""

    _attr_translation_key = "port_enabled"

    def __init__(self, coordinator: SwitchCoordinator, number: int) -> None:
        super().__init__(coordinator, number, "enabled")

    @property
    def is_on(self) -> bool | None:
        return self.port.admin_up if self.port else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_port_enabled(self._number, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_port_enabled(self._number, False)
