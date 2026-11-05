"""Websocket commands the panel uses."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
import probatio

from .const import CONF_PORT_NAMES, DOMAIN, PORT_NAME_MAX
from .coordinator import SwitchConfigEntry
from .history import RANGES
from .model import manufacturer
from .vendor import vendor_of


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands once."""
    websocket_api.async_register_command(hass, ws_snapshot)
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_history)
    websocket_api.async_register_command(hass, ws_set_port_enabled)
    websocket_api.async_register_command(hass, ws_set_port_name)


def _device_names(hass: HomeAssistant, mac: str) -> dict[str, str | None]:
    """Name and maker of a device that Home Assistant knows by this MAC address.

    Without such a device the maker still comes from the address itself, if it has one.
    """
    devices = dr.async_get(hass).async_get_devices(connections={(dr.CONNECTION_NETWORK_MAC, mac)})
    if not devices:
        return {"name": None, "manufacturer": vendor_of(mac)}
    # Several integrations can know the same MAC; take the first one that has a name.
    device = next((d for d in devices if d.name_by_user or d.name), devices[0])
    return {
        "name": device.name_by_user or device.name,
        "manufacturer": device.manufacturer or vendor_of(mac),
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
                "name": names.get(str(number), "") or port.alias,
                "custom_name": names.get(str(number), ""),
                "alias": port.alias,
                "admin_up": port.admin_up,
                "protected": coordinator.is_protected(number),
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
                "rx_pps": port.rx_pps,
                "tx_pps": port.tx_pps,
                "rx_mcast_pps": port.rx_mcast_pps,
                "rx_bcast_pps": port.rx_bcast_pps,
                "mode": port.mode,
                "flow_control": port.flow_control,
                "lag": port.lag,
                "security_max": port.security_max,
                "security_learned": port.security_learned,
                "loop": port.loop,
                "loop_blocked": port.loop_blocked,
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
        "model": data.model or data.description or None,
        "hw_version": data.hw_version,
        "sw_version": data.sw_version,
        "location": data.location,
        "contact": data.contact,
        "uptime": data.uptime,
        "interval": int(coordinator.update_interval.total_seconds())
        if coordinator.update_interval
        else 0,
        "last_update_success": coordinator.last_update_success,
        "can_write": coordinator.can_write,
        "ports": ports,
    }


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required("type"): f"{DOMAIN}/snapshot"})
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
@websocket_api.websocket_command({probatio.Required("type"): f"{DOMAIN}/subscribe"})
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
        probatio.Required("type"): f"{DOMAIN}/history",
        probatio.Required("entry_id"): str,
        probatio.Required("port"): int,
        probatio.Optional("range", default="24h"): probatio.In(list(RANGES)),
    }
)
@callback
def ws_history(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """The receive and transmit rates of one port over the last 24 hours or 7 days."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "switch not found")
        return
    now = time.time()
    bucket, keep = RANGES[msg["range"]]
    series = entry.runtime_data.history.series(msg["port"], msg["range"])
    connection.send_result(
        msg["id"],
        {
            "start": now - keep,
            "end": now,
            "bucket": bucket,
            "points": [[t, round(rx, 3), round(tx, 3)] for t, rx, tx in series],
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/set_port_enabled",
        probatio.Required("entry_id"): str,
        probatio.Required("port"): int,
        probatio.Required("enabled"): bool,
    }
)
@websocket_api.async_response
async def ws_set_port_enabled(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Switch a port on or off, if writing is allowed and the port is not protected."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "switch not found")
        return
    try:
        await entry.runtime_data.async_set_port_enabled(msg["port"], msg["enabled"])
    except ServiceValidationError as err:
        connection.send_error(msg["id"], "not_allowed", str(err))
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "write_failed", str(err))
    else:
        connection.send_result(msg["id"], {"enabled": msg["enabled"]})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/set_port_name",
        probatio.Required("entry_id"): str,
        probatio.Required("port"): probatio.All(int, probatio.Range(min=1, max=999)),
        probatio.Required("name"): probatio.All(str, probatio.Length(max=PORT_NAME_MAX)),
        probatio.Optional("to_switch", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_set_port_name(
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
    if msg["to_switch"]:
        try:
            await entry.runtime_data.async_set_port_alias(msg["port"], name)
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "write_failed", str(err))
            return
    connection.send_result(msg["id"], {"name": name})
