"""Tests for the IGMP snooping counters."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.tplink_switch_snmp import model
from custom_components.tplink_switch_snmp.const import DOMAIN

from .conftest import BRIDGE_MAC


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_the_counters_are_read_and_the_reports_add_up():
    ports = {1: _port(1), 2: _port(2)}
    extras = {
        "igmp_queries": {"1": 4},
        "igmp_report_v1": {"1": 1},
        "igmp_report_v2": {"1": 20, "2": "?"},
        "igmp_report_v3": {"1": 3},
        "igmp_leaves": {"1": 0},
        "igmp_port_on": {"1": 1, "2": 0},
    }
    model.add_igmp(ports, extras)

    assert ports[1].igmp == {"queries": 4, "reports": 24, "leaves": 0}
    assert ports[2].igmp == {}
    assert (ports[1].igmp_snooping, ports[2].igmp_snooping) == (True, False)


def test_a_switch_without_igmp_snooping():
    ports = {1: _port(1)}
    model.add_igmp(ports, {})
    assert ports[1].igmp == {}
    assert ports[1].igmp_snooping is None


async def test_sensors_exist_only_where_the_switch_reports_them(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["feat_igmp"] = {"0": 1}
    tables["igmp_queries"] = {"1": 7}
    tables["igmp_errors"] = {"1": 2}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    queries = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_igmp_queries")
    assert queries
    assert registry.async_get(queries).disabled
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_igmp_errors")
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_igmp_leaves")
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port2_igmp_queries")
    assert registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_igmp")

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    switch = (await ws.receive_json())["result"]["switches"][0]
    assert switch["ports"][0]["igmp"] == {"queries": 7, "errors": 2}
    assert switch["features"]["igmp"] is True


async def test_the_sensor_reports_the_count(hass: HomeAssistant, snmp, entry, tables) -> None:
    from custom_components.tplink_switch_snmp.sensor import PORT_SENSORS, PortSensor

    tables["igmp_queries"] = {"1": 7}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    description = next(d for d in PORT_SENSORS if d.key == "igmp_queries")
    assert PortSensor(entry.runtime_data, 1, description).native_value == 7
