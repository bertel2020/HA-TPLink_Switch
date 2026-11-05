"""Tests for the ARP protection counters."""

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.tplink_switch_snmp import logbook, model
from custom_components.tplink_switch_snmp.const import DOMAIN, EVENT_ALARM

from .conftest import BRIDGE_MAC


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def test_counters_are_read_when_the_protection_is_on():
    ports = {1: _port(1), 2: _port(2), 3: _port(3)}
    extras = {
        "arp_on": {"0": 1},
        "arp_state": {"1": 1, "2": 0},
        "arp_illegal": {"1": 0, "2": 5},
    }
    model.add_arp(ports, extras)

    assert (ports[1].arp_illegal, ports[1].arp_trusted) == (0, True)
    assert (ports[2].arp_illegal, ports[2].arp_trusted) == (5, False)
    assert (ports[3].arp_illegal, ports[3].arp_trusted) == (None, None)


def test_nothing_is_read_when_the_protection_is_off():
    ports = {1: _port(1)}
    model.add_arp(ports, {"arp_on": {"0": 0}, "arp_illegal": {"1": 9}})
    assert ports[1].arp_illegal is None


def test_a_switch_without_the_table_and_a_port_without_a_state():
    ports = {1: _port(1)}
    model.add_arp(ports, {})
    assert ports[1].arp_illegal is None
    model.add_arp(ports, {"arp_illegal": {"1": 2}})  # no enable column, no state column
    assert (ports[1].arp_illegal, ports[1].arp_trusted) == (2, None)


async def test_sensors_exist_only_where_the_switch_reports_them(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["arp_on"] = {"0": 1}
    tables["arp_illegal"] = {"1": 3}
    await _setup(hass, entry)

    registry = er.async_get(hass)
    sensor = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_arp_illegal")
    assert sensor
    assert registry.async_get(sensor).disabled
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port2_arp_illegal")

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    ports = {p["n"]: p for p in (await ws.receive_json())["result"]["switches"][0]["ports"]}
    assert ports[1]["arp_illegal"] == 3
    assert ports[2]["arp_illegal"] is None


async def test_new_illegal_packets_fire_an_alarm(hass: HomeAssistant, snmp, entry, tables) -> None:
    tables["arp_illegal"] = {"1": 3, "2": 0}
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_ALARM)

    await entry.runtime_data.async_refresh()  # the counter did not move
    await hass.async_block_till_done()
    assert events == []

    tables["arp_illegal"] = {"1": 8, "2": 0}
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert len(events) == 1
    data = events[0].data
    assert (data["alarm"], data["port"], data["count"]) == ("arp_illegal", 1, 5)
    assert data["switch"] == "TL-SG3424"


async def test_logbook_text_of_a_port_alarm(hass: HomeAssistant) -> None:
    described = {}

    @callback
    def register(domain, event_type, describe):
        described[event_type] = describe

    logbook.async_describe_events(hass, register)
    data = {"switch": "TL-SG3424", "alarm": "arp_illegal", "port": 4, "port_name": "AP"}
    result = described[EVENT_ALARM](Event(EVENT_ALARM, data))
    assert result["message"] == "Port 4 (AP): illegal ARP packets received"
