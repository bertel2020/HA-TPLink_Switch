"""Traffic, speed and MAC sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SwitchConfigEntry, SwitchCoordinator
from .entity import PortEntity, SwitchEntity
from .model import PortData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PortSensorDescription(SensorEntityDescription):
    """A sensor that reads one value of a port."""

    value_fn: Callable[[PortData], Any]


PORT_SENSORS: tuple[PortSensorDescription, ...] = (
    PortSensorDescription(
        key="rx_rate",
        translation_key="rx_rate",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda p: p.rx_rate,
    ),
    PortSensorDescription(
        key="tx_rate",
        translation_key="tx_rate",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda p: p.tx_rate,
    ),
    PortSensorDescription(
        key="speed",
        translation_key="speed",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.speed,
    ),
    PortSensorDescription(
        key="rx_total",
        translation_key="rx_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.rx_bytes,
    ),
    PortSensorDescription(
        key="tx_total",
        translation_key="tx_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.tx_bytes,
    ),
    PortSensorDescription(
        key="rx_errors",
        translation_key="rx_errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.rx_errors,
    ),
    PortSensorDescription(
        key="tx_errors",
        translation_key="tx_errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.tx_errors,
    ),
    PortSensorDescription(
        key="macs",
        translation_key="macs",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: len(p.macs),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the switch and port sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [SwitchUptime(coordinator)]
    entities.extend(
        PortSensor(coordinator, number, description)
        for number in coordinator.data.ports
        for description in PORT_SENSORS
    )
    async_add_entities(entities)


class SwitchUptime(SwitchEntity, SensorEntity):
    """How long the switch has been running."""

    _attr_translation_key = "uptime"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_unit_of_measurement = UnitOfTime.DAYS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SwitchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._mac}_uptime"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.uptime


class PortSensor(PortEntity, SensorEntity):
    """One value of one port."""

    entity_description: PortSensorDescription
    # The MAC list can be long on uplink ports; keep it out of the database.
    _unrecorded_attributes = frozenset({"mac_addresses"})

    def __init__(
        self,
        coordinator: SwitchCoordinator,
        number: int,
        description: PortSensorDescription,
    ) -> None:
        super().__init__(coordinator, number, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.port) if self.port else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key == "macs" and self.port:
            return {"mac_addresses": self.port.macs}
        return None
