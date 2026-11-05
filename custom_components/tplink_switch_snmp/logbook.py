"""Describe the switch's events in the logbook."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN, EVENT_ALARM, EVENT_DEVICE_MOVED, EVENT_LINK_CHANGED


def _port(data: Mapping[str, Any]) -> str:
    name = data.get("port_name")
    return f"Port {data['port']}" + (f" ({name})" if name else "")


ALARM_TEXTS = {
    "cpu_load": "CPU load is over 80 %",
    "memory_load": "memory use is over 80 %",
    "loop": "loop detection reports a change",
    "broadcast_storm": "broadcast storm control limit exceeded",
    "multicast_storm": "multicast storm control limit exceeded",
    "stp_topology_change": "spanning tree topology changed",
    "arp_illegal": "illegal ARP packets received",
}


def _speed(mbit: int) -> str:
    return "1 Gbit/s" if mbit == 1000 else f"{mbit} Mbit/s"


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, Any]]], None],
) -> None:
    """Register the descriptions of the events."""

    @callback
    def describe_link_changed(event: Event) -> dict[str, Any]:
        data = event.data
        if data.get("flap"):
            message = f"{_port(data)}: link was lost and came back"
        elif data["up"]:
            message = f"{_port(data)}: link up at {_speed(data['speed'])}"
        else:
            message = f"{_port(data)}: link down"
        return {
            LOGBOOK_ENTRY_NAME: data.get("switch", "Switch"),
            LOGBOOK_ENTRY_MESSAGE: message,
            LOGBOOK_ENTRY_ENTITY_ID: data.get("entity_id"),
        }

    @callback
    def describe_device_moved(event: Event) -> dict[str, Any]:
        data = event.data
        before = _port({"port": data["from_port"], "port_name": data.get("from_port_name")})
        after = _port({"port": data["to_port"], "port_name": data.get("to_port_name")})
        switch = data.get("switch", "the switch")
        return {
            LOGBOOK_ENTRY_NAME: data.get("name") or data["mac"],
            LOGBOOK_ENTRY_MESSAGE: f"moved from {before} to {after} at {switch}",
        }

    @callback
    def describe_alarm(event: Event) -> dict[str, Any]:
        data = event.data
        message = ALARM_TEXTS.get(data["alarm"], data["alarm"])
        if "port" in data:
            message = f"{_port(data)}: {message}"
        return {LOGBOOK_ENTRY_NAME: data.get("switch", "Switch"), LOGBOOK_ENTRY_MESSAGE: message}

    async_describe_event(DOMAIN, EVENT_ALARM, describe_alarm)
    async_describe_event(DOMAIN, EVENT_LINK_CHANGED, describe_link_changed)
    async_describe_event(DOMAIN, EVENT_DEVICE_MOVED, describe_device_moved)
