"""Tests for the RMON counters that tell the errors of a port apart."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.tplink_switch_snmp import model
from custom_components.tplink_switch_snmp.const import DOMAIN, OID_RMON_STATS
from custom_components.tplink_switch_snmp.snmp import SnmpError

from .conftest import BRIDGE_MAC


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_counters_follow_the_interface_named_by_the_data_source():
    ports = {1: _port(1), 2: _port(2)}
    extras = {
        # row 10 counts interface 2, row 7 has no source that can be read, row 99 is no port
        "rmon_source": {"10": b"1.3.6.1.2.1.2.2.1.1.2", "7": b"?", "99": b"1.3.6.1.2.1.2.2.1.1.99"},
        "rmon_crc": {"10": 5, "7": 1, "99": 1},
        "rmon_coll": {"10": 2},
        "rmon_frag": {"10": b"not a number"},
    }
    model.add_error_details(ports, extras)

    assert ports[2].error_details == {"crc_errors": 5, "collisions": 2}
    assert ports[1].error_details == {}


def test_a_row_without_a_source_column_value_is_the_port_itself():
    ports = {1: _port(1)}
    model.add_error_details(ports, {"rmon_source": {"1": b""}, "rmon_crc": {"1": 3}})
    assert ports[1].error_details == {"crc_errors": 3}


def test_a_switch_without_rmon_has_no_details():
    ports = {1: _port(1)}
    model.add_error_details(ports, {})
    assert ports[1].error_details == {}


async def test_sensors_exist_only_where_the_switch_reports_them(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["rmon_source"] = {"1": b"1.3.6.1.2.1.2.2.1.1.1"}
    tables["rmon_crc"] = {"1": 4}
    tables["rmon_coll"] = {"1": 0}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    crc = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_crc_errors")
    assert crc
    assert registry.async_get(crc).disabled  # off by default, like the other error counters
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_collisions")
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_jabbers")
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port2_crc_errors")


async def test_the_panel_gets_the_details(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["rmon_source"] = {"1": b"1.3.6.1.2.1.2.2.1.1.1"}
    tables["rmon_crc"] = {"1": 4}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    ports = {p["n"]: p for p in (await ws.receive_json())["result"]["switches"][0]["ports"]}

    assert ports[1]["error_details"] == {"crc_errors": 4}
    assert ports[2]["error_details"] == {}


async def test_a_switch_that_refuses_rmon_is_still_polled(hass: HomeAssistant, snmp, entry) -> None:
    original = snmp.walk_many.side_effect

    def walk_many(oids):
        if any(oid.startswith(OID_RMON_STATS) for oid in oids.values()):
            raise SnmpError("noSuchName")
        return original(oids)

    snmp.walk_many.side_effect = walk_many
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.data.ports[1].error_details == {}
