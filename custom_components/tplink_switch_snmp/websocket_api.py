"""Websocket commands the panel uses."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_PORT_NAMES, DOMAIN, PORT_NAME_MAX
from .coordinator import SwitchConfigEntry

# (platform, key) of the entities whose history the panel draws
HISTORY_KEYS = (("sensor", "rx_rate"), ("sensor", "tx_rate"))


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands once."""
    websocket_api.async_register_command(hass, ws_snapshot)
    websocket_api.async_register_command(hass, ws_set_port_name)


def _device_names(hass: HomeAssistant, mac: str) -> dict[str, str | None]:
    """Name and maker of a device that Home Assistant knows by this MAC address."""
    device = dr.async_get(hass).async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mac)}
    )
    if device is None:
        return {"name": None, "manufacturer": None}
    return {
        "name": device.name_by_user or device.name,
        "manufacturer": device.manufacturer,
    }


def _switch(hass: HomeAssistant, entry: SwitchConfigEntry) -> dict[str, Any]:
    """Everything the panel shows about one switch."""
    coordinator = entry.runtime_data
    data = coordinator.data
    registry = er.async_get(hass)
    names = entry.options.get(CONF_PORT_NAMES, {})
    ports = []
    for number, port in sorted(data.ports.items()):
        entities = {}
        for platform, key in HISTORY_KEYS:
            entity_id = registry.async_get_entity_id(
                platform, DOMAIN, f"{entry.unique_id}_port{number}_{key}"
            )
            if entity_id:
                entities[key] = entity_id
        ports.append(
            {
                "n": number,
                "name": names.get(str(number), ""),
                "if_name": port.name,
                "up": port.up,
                "speed": port.speed,
                "rx_rate": port.rx_rate,
                "tx_rate": port.tx_rate,
                "rx_bytes": port.rx_bytes,
                "tx_bytes": port.tx_bytes,
                "rx_errors": port.rx_errors,
                "tx_errors": port.tx_errors,
                "macs": [{"mac": mac, **_device_names(hass, mac)} for mac in port.macs],
                "entities": entities,
            }
        )
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "host": entry.data["host"],
        "mac": entry.unique_id,
        "description": data.description,
        "uptime": data.uptime,
        "interval": int(coordinator.update_interval.total_seconds()),
        "last_update_success": coordinator.last_update_success,
        "ports": ports,
    }


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/snapshot"})
@callback
def ws_snapshot(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """All switches with their ports."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    connection.send_result(
        msg["id"], {"switches": [_switch(hass, entry) for entry in entries]}
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set_port_name",
        vol.Required("entry_id"): str,
        vol.Required("port"): vol.All(int, vol.Range(min=1, max=999)),
        vol.Required("name"): vol.All(str, vol.Length(max=PORT_NAME_MAX)),
    }
)
@callback
def ws_set_port_name(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Give a port a name of your own; an empty name removes it."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "not_found", "switch not found")
        return
    names = dict(entry.options.get(CONF_PORT_NAMES, {}))
    name = msg["name"].strip()
    if name:
        names[str(msg["port"])] = name
    else:
        names.pop(str(msg["port"]), None)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_PORT_NAMES: names}
    )
    connection.send_result(msg["id"], {"name": name})
