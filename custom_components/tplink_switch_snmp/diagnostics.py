"""Diagnostics: what a bug report needs, without addresses, names or credentials."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import (
    CONF_AUTH_KEY,
    CONF_COMMUNITY,
    CONF_PORT_NAMES,
    CONF_PRIV_KEY,
    CONF_USERNAME,
    CONF_VERSION,
    DEFAULT_VERSION,
)
from .coordinator import SwitchConfigEntry

TO_REDACT = {CONF_HOST, CONF_COMMUNITY, CONF_USERNAME, CONF_AUTH_KEY, CONF_PRIV_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SwitchConfigEntry
) -> dict[str, Any]:
    """Return the diagnostics of one switch."""
    coordinator = entry.runtime_data
    data = coordinator.data
    options = dict(entry.options)
    # The names are the user's own text; say how many there are, not what they are.
    options[CONF_PORT_NAMES] = len(options.get(CONF_PORT_NAMES, {}))
    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": options,
            "snmp_version": entry.data.get(CONF_VERSION, DEFAULT_VERSION),
        },
        "switch": {
            "description": data.description,
            "object_id": data.object_id,
            "uptime": data.uptime,
            "polling_interval": coordinator.update_interval.total_seconds(),
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
            "learned_macs": len(data.mac_ports),
        },
        "ports": [
            {
                "number": port.number,
                "if_index": port.if_index,
                "interface": port.name,
                "up": port.up,
                "speed": port.speed,
                "rx_bytes": port.rx_bytes,
                "tx_bytes": port.tx_bytes,
                "rx_errors": port.rx_errors,
                "tx_errors": port.tx_errors,
                "rx_discards": port.rx_discards,
                "tx_discards": port.tx_discards,
                "rx_rate": port.rx_rate,
                "tx_rate": port.tx_rate,
                "last_change": port.last_change,
                "macs": len(port.macs),
            }
            for port in data.ports.values()
        ],
    }
