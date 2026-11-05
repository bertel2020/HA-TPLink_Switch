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
    PERCENTAGE,
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ERROR_DETAILS
from .coordinator import SwitchConfigEntry, SwitchCoordinator
from .entity import PortEntity, SwitchEntity
from .model import PortData
from .selection import selected_groups, wants

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
        key="crc_errors",
        translation_key="crc_errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.error_details.get("crc_errors"),
    ),
    PortSensorDescription(
        key="undersize_packets",
        translation_key="undersize_packets",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.error_details.get("undersize_packets"),
    ),
    PortSensorDescription(
        key="oversize_packets",
        translation_key="oversize_packets",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.error_details.get("oversize_packets"),
    ),
    PortSensorDescription(
        key="fragments",
        translation_key="fragments",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.error_details.get("fragments"),
    ),
    PortSensorDescription(
        key="jabbers",
        translation_key="jabbers",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.error_details.get("jabbers"),
    ),
    PortSensorDescription(
        key="collisions",
        translation_key="collisions",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.error_details.get("collisions"),
    ),
    PortSensorDescription(
        key="arp_illegal",
        translation_key="arp_illegal",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.arp_illegal,
    ),
    PortSensorDescription(
        key="pvid",
        translation_key="pvid",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.pvid,
    ),
    PortSensorDescription(
        key="rx_discards",
        translation_key="rx_discards",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.rx_discards,
    ),
    PortSensorDescription(
        key="tx_discards",
        translation_key="tx_discards",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.tx_discards,
    ),
    PortSensorDescription(
        key="rx_packets",
        translation_key="rx_packets",
        native_unit_of_measurement="pkt/s",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.rx_pps,
    ),
    PortSensorDescription(
        key="tx_packets",
        translation_key="tx_packets",
        native_unit_of_measurement="pkt/s",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.tx_pps,
    ),
    PortSensorDescription(
        key="rx_broadcast",
        translation_key="rx_broadcast",
        native_unit_of_measurement="pkt/s",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.rx_bcast_pps,
    ),
    PortSensorDescription(
        key="rx_multicast",
        translation_key="rx_multicast",
        native_unit_of_measurement="pkt/s",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.rx_mcast_pps,
    ),
    PortSensorDescription(
        key="rx_utilization",
        translation_key="rx_utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.rx_util,
    ),
    PortSensorDescription(
        key="tx_utilization",
        translation_key="tx_utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.tx_util,
    ),
    PortSensorDescription(
        key="link_changed",
        translation_key="link_changed",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda p: p.link_changed_at,
    ),
    PortSensorDescription(
        key="macs",
        translation_key="macs",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: len(p.macs),
    ),
)


def _reported(key: str, port: PortData) -> bool:
    """Whether the switch reports the value; some sensors exist only where it does."""
    if key in ERROR_DETAILS:
        return key in port.error_details
    if key == "arp_illegal":
        return port.arp_illegal is not None
    if key == "pvid":
        return port.pvid is not None
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the switch and port sensors."""
    coordinator = entry.runtime_data
    groups = selected_groups(entry)
    entities: list[SensorEntity] = [SwitchUptime(coordinator)] if "uptime" in groups else []
    if "stp" in groups and coordinator.data.stp_changes is not None:
        entities.append(SwitchStpChanges(coordinator))
    entities.extend(
        PortSensor(coordinator, number, description)
        for number in coordinator.data.ports
        for description in PORT_SENSORS
        if wants(entry, number, description.key)
        and _reported(description.key, coordinator.data.ports[number])
    )
    async_add_entities(entities)

    # A port sensor for every device that Home Assistant knows by its MAC address,
    # including devices that show up at the switch or in the registry later on.
    known: set[str] = set()

    registry = er.async_get(hass)
    prefix = f"{entry.unique_id}_device_"

    @callback
    def remove_stale() -> None:
        """Remove the port sensor of a device that Home Assistant no longer has."""
        for reg in er.async_entries_for_config_entry(registry, entry.entry_id):
            if reg.translation_key != "device_port":
                continue
            mac = reg.unique_id.removeprefix(prefix).removesuffix("_port")
            if coordinator.known_device(mac) is None:
                registry.async_remove(reg.entity_id)
                known.discard(mac)

    @callback
    def add_devices() -> None:
        remove_stale()
        new = []
        for mac in coordinator.data.mac_ports:
            if mac in known:
                continue
            device = coordinator.known_device(mac)
            if device is not None:
                known.add(mac)
                new.append(DevicePort(coordinator, mac, device.name_by_user or device.name or mac))
        if new:
            async_add_entities(new)

    if "devices" in groups:
        add_devices()
        entry.async_on_unload(coordinator.async_add_listener(add_devices))


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


class SwitchStpChanges(SwitchEntity, SensorEntity):
    """How often the spanning tree topology has changed: a restless network shows here."""

    _attr_translation_key = "stp_changes"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SwitchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._mac}_stp_changes"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.stp_changes


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
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = super().extra_state_attributes
        if self.entity_description.key == "macs" and self.port:
            attributes["mac_addresses"] = self.port.macs
        if self.entity_description.key == "pvid" and self.port:
            attributes["untagged"] = self.port.vlans_untagged
            attributes["tagged"] = self.port.vlans_tagged
        return attributes


class DevicePort(SwitchEntity, SensorEntity):
    """The switch port a device that Home Assistant knows is plugged into.

    The sensor belongs to the switch: a device can only belong to one integration, so it
    cannot sit on the other integration's device. It is named after that device instead.
    """

    _attr_translation_key = "device_port"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SwitchCoordinator, mac: str, name: str) -> None:
        super().__init__(coordinator)
        self._device_mac = mac
        self._device_name = name
        self._attr_unique_id = f"{self._mac}_device_{mac}_port"
        self._attr_translation_placeholders = {"device": name}

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.mac_ports.get(self._device_mac)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        number = self.native_value
        return {
            "mac": self._device_mac,
            "device_name": self._device_name,
            "port_name": self.coordinator.port_label(number) if number is not None else "",
        }
