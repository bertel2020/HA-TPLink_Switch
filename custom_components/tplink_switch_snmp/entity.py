"""Base entity for the switch."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SwitchCoordinator
from .model import PortData, manufacturer


class SwitchEntity(CoordinatorEntity[SwitchCoordinator]):
    """An entity that belongs to the switch."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SwitchCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._mac = entry.unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            connections={(CONNECTION_NETWORK_MAC, entry.unique_id)},
            manufacturer=manufacturer(coordinator.data.object_id),
            model=coordinator.data.model or coordinator.data.description or None,
            hw_version=coordinator.data.hw_version,
            sw_version=coordinator.data.sw_version,
            name=entry.title,
            configuration_url=f"http://{entry.data[CONF_HOST]}/",
        )


class PortEntity(SwitchEntity):
    """An entity that belongs to one port."""

    def __init__(self, coordinator: SwitchCoordinator, number: int, key: str) -> None:
        super().__init__(coordinator)
        self._number = number
        self._attr_unique_id = f"{self._mac}_port{number}_{key}"
        self._attr_translation_placeholders = {"port": str(number)}

    @property
    def port(self) -> PortData | None:
        """The latest data of this port."""
        return self.coordinator.data.ports.get(self._number)

    @property
    def available(self) -> bool:
        return super().available and self.port is not None
