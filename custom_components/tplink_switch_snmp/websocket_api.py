"""Websocket commands the panel uses."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
import voluptuous as vol

from .const import CONF_PORT_NAMES, DOMAIN, PORT_NAME_MAX
from .coordinator import SwitchConfigEntry
from .history import BUCKET, KEEP
from .model import manufacturer


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands once."""
    websocket_api.async_register_command(hass, ws_snapshot)
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_history)
    websocket_api.async_register_command(hass, ws_set_port_name)


def _device_names(hass: HomeAssistant, mac: str) -> dict[str, str | None]:
    """Name and maker of a device that Home Assistant knows by this MAC address."""
    devices = dr.async_get(hass).async_get_devices(connections={(dr.CONNECTION_NETWORK_MAC, mac)})
    if not devices:
        return {"name": None, "manufacturer": None}
    # Several integrations can know the same MAC; take the first one that has a name.
    device = next((d for d in devices if d.name_by_user or d.name), devices[0])
    return {
        "name": device.name_by_user or device.name,
        "manufacturer": device.manufacturer,
    }


def _switch(hass: HomeAssistant, entry: SwitchConfigEntry) -> dict[str, Any]:
    """Everything the panel shows about one switch."""
    coordinator = entry.runtime_data
    data = coordinator.data
    names = entry.options.get(CONF_PORT_NAMES, {})
    ports = []
    for number, port in sorted(data.ports.items()):
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
                "rx_discards": port.rx_discards,
                "tx_discards": port.tx_discards,
                "link_changed_at": port.link_changed_at.isoformat()
                if port.link_changed_at
                else None,
                "rx_util": port.rx_util,
                "tx_util": port.tx_util,
                "macs": [{"mac": mac, **_device_names(hass, mac)} for mac in port.macs],
            }
        )
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "host": entry.data["host"],
        "mac": entry.unique_id,
        "description": data.description,
        "manufacturer": manufacturer(data.object_id),
        "model": data.description or None,
        "uptime": data.uptime,
        "interval": int(coordinator.update_interval.total_seconds()),
        "last_update_success": coordinator.last_update_success,
        "ports": ports,
    }


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/snapshot"})
@callback
def ws_snapshot(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """All switches with their ports."""
    connection.send_result(msg["id"], _snapshot(hass))


def _snapshot(hass: HomeAssistant) -> dict[str, Any]:
    return {
        "switches": [
            _switch(hass, entry) for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        ]
    }


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Send the snapshot each time a switch has been polled, so the panel does not poll."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)

    @callback
    def send() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], _snapshot(hass)))

    unsubscribers = [entry.runtime_data.async_add_listener(send) for entry in entries]

    @callback
    def unsubscribe() -> None:
        for remove in unsubscribers:
            remove()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/history",
        vol.Required("entry_id"): str,
        vol.Required("port"): int,
    }
)
@callback
def ws_history(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """The receive and transmit rates of one port over the last 24 hours."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "switch not found")
        return
    now = time.time()
    connection.send_result(
        msg["id"],
        {
            "start": now - KEEP,
            "end": now,
            "bucket": BUCKET,
            "points": [
                [t, round(rx, 3), round(tx, 3)]
                for t, rx, tx in entry.runtime_data.history.series(msg["port"])
            ],
        },
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
    hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_PORT_NAMES: names})
    connection.send_result(msg["id"], {"name": name})
