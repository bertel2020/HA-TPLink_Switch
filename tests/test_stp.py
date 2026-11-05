"""Tests for the spanning tree state."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.tplink_switch_snmp import model
from custom_components.tplink_switch_snmp.const import DOMAIN, ENTITY_GROUPS, EVENT_ALARM

from .conftest import BRIDGE_MAC


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def test_states_changes_and_root_port_are_read():
    ports = {1: _port(1), 2: _port(2), 3: _port(3)}
    extras = {
        "stp_state": {"1": 5, "2": 2, "3": 99, "7": 5},  # 99 is unknown, 7 is no port
        "stp_changes": {"0": 12},
        "stp_root_port": {"0": 2},
    }
    changes, root = model.add_stp(ports, extras, {"1": 1, "2": 2, "3": 3})

    assert [p.stp_state for p in ports.values()] == ["forwarding", "blocking", None]
    assert (changes, root) == (12, 2)


def test_this_switch_as_root_has_no_root_port():
    ports = {1: _port(1)}
    changes, root = model.add_stp(ports, {"stp_changes": {"0": 0}, "stp_root_port": {"0": 0}}, {})
    assert (changes, root) == (0, None)


def test_a_switch_without_spanning_tree():
    ports = {1: _port(1)}
    assert model.add_stp(ports, {}, {"1": 1}) == (None, None)
    assert ports[1].stp_state is None


def test_ports_are_found_by_the_bridge_port_table():
    ports = {5: model.PortData(5, 5, "port 5", True, 1000, 0, 0, 0, 0)}
    model.add_stp(ports, {"stp_state": {"1": 2}}, {"1": 5})  # bridge port 1 is interface 5
    assert ports[5].stp_state == "blocking"


async def test_sensor_and_panel_follow_the_switch(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["stp_changes"] = {"0": 3}
    tables["stp_root_port"] = {"0": 1}
    tables["stp_state"] = {"1": 5, "2": 2}
    await _setup(hass, entry)

    registry = er.async_get(hass)
    sensor = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_stp_changes")
    assert sensor
    assert registry.async_get(sensor).disabled

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    switch = (await ws.receive_json())["result"]["switches"][0]
    assert (switch["stp_changes"], switch["stp_root_port"]) == (3, 1)
    assert [p["stp_state"] for p in switch["ports"]] == ["forwarding", "blocking"]


async def test_no_sensor_without_spanning_tree(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    registry = er.async_get(hass)
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_stp_changes")


async def test_a_topology_change_fires_an_alarm(hass: HomeAssistant, snmp, entry, tables) -> None:
    tables["stp_changes"] = {"0": 3}
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_ALARM)

    await entry.runtime_data.async_refresh()  # nothing changed
    await hass.async_block_till_done()
    assert events == []

    tables["stp_changes"] = {"0": 4}
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert [e.data["alarm"] for e in events] == ["stp_topology_change"]
    assert events[0].data["entry_id"] == entry.entry_id


async def test_deselecting_the_group_removes_the_sensor(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["stp_changes"] = {"0": 3}
    await _setup(hass, entry)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_stp_changes")

    groups = [group for group in ENTITY_GROUPS if group != "stp"]
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "entity_groups": groups}
    )
    await hass.async_block_till_done()

    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_stp_changes")


async def test_the_sensor_reports_the_counter(hass: HomeAssistant, snmp, entry, tables) -> None:
    from custom_components.tplink_switch_snmp.sensor import SwitchStpChanges

    tables["stp_changes"] = {"0": 7}
    await _setup(hass, entry)

    # the sensor is off by default, so Home Assistant never asks for its value
    assert SwitchStpChanges(entry.runtime_data).native_value == 7
