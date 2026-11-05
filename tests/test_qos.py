"""Tests for the QoS priority of the ports and the scheduler of the switch."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.tplink_switch_snmp import model
from custom_components.tplink_switch_snmp.const import DOMAIN, ENTITY_GROUPS

from .conftest import BRIDGE_MAC


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_priorities_and_scheduler_are_read():
    ports = {1: _port(1), 2: _port(2)}
    mode = model.add_qos(ports, {"qos_priority": {"1": 5, "2": "?"}, "qos_mode": {"0": 1}})

    assert mode == "wrr"
    assert (ports[1].qos_priority, ports[2].qos_priority) == (5, None)


def test_a_switch_without_qos():
    ports = {1: _port(1)}
    assert model.add_qos(ports, {}) is None
    assert model.add_qos(ports, {"qos_mode": {"0": 99}}) is None  # not a mode we know
    assert ports[1].qos_priority is None


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities_and_panel_follow_the_switch(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    from custom_components.tplink_switch_snmp.sensor import PORT_SENSORS, PortSensor, SwitchQosMode

    tables["qos_mode"] = {"0": 0}
    tables["qos_priority"] = {"1": 6}
    tables["feat_dscp"] = {"0": 1}
    await _setup(hass, entry)

    registry = er.async_get(hass)
    mode = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_qos_mode")
    assert mode
    assert registry.async_get(mode).disabled
    priority = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_qos_priority")
    assert priority
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port2_qos_priority")
    assert registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_dscp")

    assert SwitchQosMode(entry.runtime_data).native_value == "sp"
    description = next(d for d in PORT_SENSORS if d.key == "qos_priority")
    assert PortSensor(entry.runtime_data, 1, description).native_value == 6

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    switch = (await ws.receive_json())["result"]["switches"][0]
    assert (switch["qos_mode"], switch["ports"][0]["qos_priority"]) == ("sp", 6)
    assert switch["features"]["dscp"] is True


async def test_no_sensors_without_qos(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    registry = er.async_get(hass)
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_qos_mode")


async def test_deselecting_the_group_removes_the_scheduler_sensor(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["qos_mode"] = {"0": 3}
    await _setup(hass, entry)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_qos_mode")

    groups = [group for group in ENTITY_GROUPS if group != "qos"]
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "entity_groups": groups}
    )
    await hass.async_block_till_done()

    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_qos_mode")
