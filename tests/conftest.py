"""Shared fixtures: a fake switch that answers instead of a real SNMP agent."""

from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp.const import (
    CONF_COMMUNITY,
    DOMAIN,
    OID_BRIDGE_ADDRESS,
    OID_SYS_CONTACT,
    OID_SYS_DESCR,
    OID_SYS_LOCATION,
    OID_SYS_NAME,
    OID_SYS_OBJECT_ID,
    OID_SYS_UPTIME,
    OID_TPLINK_FIRMWARE,
    OID_TPLINK_HARDWARE,
)

BRIDGE_MAC = "64:66:b3:6c:28:64"
MAC_PRINTER = "00:04:20:f9:36:02"
MAC_OTHER = "00:08:dc:54:95:46"

SYSTEM = {
    OID_SYS_NAME: b"TL-SG3424",
    OID_SYS_DESCR: b"JetStream 24-Port Gigabit L2 Managed Switch",
    OID_SYS_OBJECT_ID: "1.3.6.1.4.1.11863.1.1.3",
    OID_SYS_LOCATION: b"Technikraum",
    OID_SYS_CONTACT: b"Roberto",
    OID_TPLINK_HARDWARE: b"TL-SG3424 1.0",
    OID_TPLINK_FIRMWARE: b"1.11.10 Build 20150713 Rel.53496(n)",
    OID_SYS_UPTIME: 158 * 86400 * 100,  # timeticks: hundredths of a second
    OID_BRIDGE_ADDRESS: bytes.fromhex("6466b36c2864"),
}

# What the walks of the real switch return, reduced to two ports and one other interface.
TABLES = {
    "name": {"1": b"port 1: Gigabit Copper", "2": b"port 2: Gigabit Copper", "25": b"AUX"},
    "oper": {"1": 1, "2": 2, "25": 1},
    "speed": {"1": 1000, "2": 0, "25": 0},
    "rx": {"1": 1_000_000, "2": 0, "25": 0},
    "tx": {"1": 2_000_000, "2": 0, "25": 0},
    "rx_err": {"1": 0, "2": 0, "25": 0},
    "tx_err": {"1": 3, "2": 0, "25": 0},
    "last_change": {"1": 1000, "2": 500, "25": 0},
    "rx_disc": {"1": 7, "2": 0, "25": 0},
    "tx_disc": {"1": 0, "2": 0, "25": 0},
    "fdb_q": {"1.0.4.32.249.54.2": 1, "1.0.8.220.84.149.70": 1},
    "fdb": {},
    "base_port": {"1": 1, "2": 2},
}


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from this repository."""


@pytest.fixture
def tables() -> dict:
    """The walk results; a test changes them to simulate traffic."""
    return deepcopy(TABLES)


@pytest.fixture
def snmp(tables):
    """Replace the SNMP client and engine in the integration and its config flow."""
    client = MagicMock()
    client.get = AsyncMock(side_effect=lambda *oids: {o: SYSTEM[o] for o in oids if o in SYSTEM})
    client.walk_many = AsyncMock(side_effect=lambda _oids: deepcopy(tables))
    client.close = MagicMock()
    base = "custom_components.tplink_switch_snmp"
    with (
        patch(f"{base}.SnmpClient", return_value=client),
        patch(f"{base}.SnmpEngine"),
        patch(f"{base}.config_flow.SnmpClient", return_value=client),
        patch(f"{base}.config_flow.SnmpEngine"),
    ):
        yield client


@pytest.fixture
def entry() -> MockConfigEntry:
    """A configured switch."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="TL-SG3424",
        unique_id=BRIDGE_MAC,
        data={
            "host": "192.168.79.15",
            "port": 161,
            "version": "2c",
            CONF_COMMUNITY: "homeassistant",
        },
    )
