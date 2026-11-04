"""Describe the switch's events in the logbook."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN, EVENT_DEVICE_MOVED, EVENT_LINK_CHANGED


def _port(data: dict[str, Any]) -> str:
    name = data.get("port_name")
    return f"Port {data['port']}" + (f" ({name})" if name else "")


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

    async_describe_event(DOMAIN, EVENT_LINK_CHANGED, describe_link_changed)
    async_describe_event(DOMAIN, EVENT_DEVICE_MOVED, describe_device_moved)
