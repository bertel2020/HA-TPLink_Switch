"""Buttons for what the switch can be told to do: save the configuration, restart."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SwitchConfigEntry, SwitchCoordinator
from .entity import SwitchEntity
from .model import manufacturer

PARALLEL_UPDATES = 1  # one write at a time


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the buttons, but only if the options allow writing and the switch is a TP-Link."""
    coordinator = entry.runtime_data
    if coordinator.can_write and manufacturer(coordinator.data.object_id) == "TP-Link":
        async_add_entities([SaveConfig(coordinator), Reboot(coordinator)])


class SaveConfig(SwitchEntity, ButtonEntity):
    """Write the running configuration to the flash, so that a restart keeps it."""

    _attr_translation_key = "save_config"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SwitchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._mac}_save_config"

    async def async_press(self) -> None:
        await self.coordinator.async_save_config()


class Reboot(SwitchEntity, ButtonEntity):
    """Restart the switch. Off by default: it cuts every device off for a minute."""

    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SwitchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._mac}_reboot"

    async def async_press(self) -> None:
        await self.coordinator.async_reboot()
