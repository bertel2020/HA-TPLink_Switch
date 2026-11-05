"""Tests for the on/off state of DoS defence, DHCP snooping and 802.1X, and the extra alarms."""

import json
from pathlib import Path

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.tplink_switch_snmp import logbook, model
from custom_components.tplink_switch_snmp.const import (
    DOMAIN,
    ENTITY_GROUPS,
    EVENT_ALARM,
    FEATURES,
    TRAP_ALARMS,
)

from .conftest import BRIDGE_MAC

BASE = Path(__file__).parents[1] / "custom_components/tplink_switch_snmp"


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_the_functions_are_read_and_the_trusted_ports_with_them():
    ports = {1: _port(1), 2: _port(2), 3: _port(3)}
    extras = {
        "feat_dos": {"0": 0},
        "feat_dhcp": {"0": 1},
        "feat_8021x": {"0": "?"},  # not a number: the switch does not say
        "dhcp_trust": {"1": 1, "2": 0, "3": "?"},
    }
    features = model.add_features(ports, extras)

    assert features == {"dos": False, "dhcp": True}
    assert [p.dhcp_trusted for p in ports.values()] == [True, False, None]


def test_without_dhcp_snooping_no_port_is_trusted():
    ports = {1: _port(1)}
    model.add_features(ports, {"feat_dhcp": {"0": 0}, "dhcp_trust": {"1": 1}})
    assert ports[1].dhcp_trusted is None
    assert model.add_features(ports, {}) == {}


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_sensors_exist_only_for_what_the_switch_tells(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["feat_dos"] = {"0": 1}
    tables["feat_dhcp"] = {"0": 1}
    tables["dhcp_trust"] = {"2": 1}
    await _setup(hass, entry)

    registry = er.async_get(hass)
    dos = registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_dos")
    assert dos
    assert registry.async_get(dos).disabled
    assert registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_dhcp")
    assert not registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_dot1x")

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    switch = (await ws.receive_json())["result"]["switches"][0]
    assert switch["features"] == {"dos": True, "dhcp": True}
    assert [p["dhcp_trusted"] for p in switch["ports"]] == [None, True]


async def test_a_sensor_reports_whether_the_function_is_on(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    from custom_components.tplink_switch_snmp.binary_sensor import SwitchFeature

    tables["feat_dos"] = {"0": 1}
    tables["feat_dhcp"] = {"0": 0}
    await _setup(hass, entry)

    assert SwitchFeature(entry.runtime_data, "dos").is_on is True
    assert SwitchFeature(entry.runtime_data, "dhcp").is_on is False


async def test_deselecting_the_group_removes_the_sensors(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["feat_dos"] = {"0": 1}
    await _setup(hass, entry)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_dos")

    groups = [group for group in ENTITY_GROUPS if group != "security"]
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "entity_groups": groups}
    )
    await hass.async_block_till_done()

    assert not registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_dos")


def test_every_function_has_a_name_in_every_language_and_an_icon():
    for path in ("strings.json", "translations/de.json", "translations/en.json"):
        names = json.loads((BASE / path).read_text())["entity"]["binary_sensor"]
        assert {f"feature_{name}" for name in FEATURES} <= set(names), path
    icons = json.loads((BASE / "icons.json").read_text())["entity"]["binary_sensor"]
    assert {f"feature_{name}" for name in FEATURES} <= set(icons)


async def test_the_new_traps_are_alarms_with_a_text(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_ALARM)

    for trap in (
        "1.3.6.1.4.1.11863.1.1.3.6.4.3",
        "1.3.6.1.4.1.11863.1.1.3.6.4.4",
        "1.3.6.1.4.1.11863.1.1.3.1.5",
    ):
        entry.runtime_data.fire_alarm(trap)
    await hass.async_block_till_done()
    assert [e.data["alarm"] for e in events] == ["ingress_rate", "egress_rate", "config_changed"]

    described = {}

    @callback
    def register(domain, event_type, describe):
        described[event_type] = describe

    logbook.async_describe_events(hass, register)
    for alarm in ("ingress_rate", "egress_rate", "config_changed"):
        data = {"switch": "TL-SG3424", "alarm": alarm}
        assert described[EVENT_ALARM](Event(EVENT_ALARM, data))["message"] != alarm
    assert set(TRAP_ALARMS.values()) >= {"ingress_rate", "egress_rate", "config_changed"}
