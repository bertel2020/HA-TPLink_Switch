"""Which entities the options ask for."""

from __future__ import annotations

import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_ENTITY_GROUPS,
    CONF_ENTITY_PORTS,
    ENTITY_GROUPS,
    FEATURES,
    PORT_ENTITY_GROUPS,
)
from .coordinator import SwitchConfigEntry

_KEY_GROUP = {key: group for group, keys in PORT_ENTITY_GROUPS.items() for key in keys}
_PORT_ID = re.compile(r"_port(\d+)_(\w+)$")


def selected_groups(entry: SwitchConfigEntry) -> frozenset[str]:
    """The groups of entities to create; all of them unless the options say otherwise."""
    groups = entry.options.get(CONF_ENTITY_GROUPS)
    return frozenset(ENTITY_GROUPS if groups is None else groups)


def selected_ports(entry: SwitchConfigEntry) -> frozenset[int] | None:
    """The ports to create entities for, or None for all of them."""
    ports = entry.options.get(CONF_ENTITY_PORTS)
    return frozenset(int(n) for n in ports) if ports else None


def selection_key(entry: SwitchConfigEntry) -> tuple[frozenset[str], frozenset[int] | None]:
    """What the selection is, to tell whether the options changed it."""
    return selected_groups(entry), selected_ports(entry)


def wants_port(entry: SwitchConfigEntry, number: int) -> bool:
    """Whether the options leave this port in."""
    ports = selected_ports(entry)
    return ports is None or number in ports


def wants(entry: SwitchConfigEntry, number: int, key: str) -> bool:
    """Whether the entity with this key at this port is to be created."""
    group = _KEY_GROUP.get(key)
    return wants_port(entry, number) and (group is None or group in selected_groups(entry))


def async_remove_unwanted(hass: HomeAssistant, entry: SwitchConfigEntry) -> None:
    """Remove the entities from the registry that the options no longer ask for."""
    registry = er.async_get(hass)
    groups = selected_groups(entry)
    for reg in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg.unique_id.endswith("_uptime"):
            unwanted = "uptime" not in groups
        elif reg.unique_id.endswith("_stp_changes"):
            unwanted = "stp" not in groups
        elif reg.unique_id.endswith("_qos_mode"):
            unwanted = "qos" not in groups
        elif reg.unique_id.rpartition("_feature_")[2] in FEATURES:
            unwanted = FEATURES[reg.unique_id.rpartition("_feature_")[2]][0] not in groups
        elif reg.translation_key == "device_port":
            unwanted = "devices" not in groups
        elif match := _PORT_ID.search(reg.unique_id):
            unwanted = not wants(entry, int(match[1]), match[2])
        else:
            continue
        if unwanted:
            registry.async_remove(reg.entity_id)
