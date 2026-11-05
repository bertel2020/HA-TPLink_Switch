"""Tests for the VLAN membership of the ports."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.tplink_switch_snmp import model
from custom_components.tplink_switch_snmp.const import DOMAIN

from .conftest import BRIDGE_MAC


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_a_port_list_is_a_bit_per_port():
    assert model.bitmap_ports(bytes([0b10100000, 0b00000001])) == {1, 3, 16}
    assert model.bitmap_ports(b"") == set()
    assert model.bitmap_ports(5) == set()  # not a port list


def test_pvid_and_membership_are_read():
    ports = {1: _port(1), 2: _port(2), 3: _port(3)}
    extras = {
        "vlan_pvid": {"1": 10, "2": 1, "9": 1, "3": "x"},  # 9 is no port, "x" is no number
        "vlan_name": {"1": b"default", "10": b"IoT", "x": b"?"},
        "vlan_egress": {"1": bytes([0b01100000]), "10": bytes([0b10100000])},
        "vlan_untagged": {"1": bytes([0b01100000]), "10": bytes([0b10000000])},
    }
    names = model.add_vlans(ports, extras, {"1": 1, "2": 2, "3": 3})

    assert names == {1: "default", 10: "IoT"}
    assert (ports[1].pvid, ports[2].pvid, ports[3].pvid) == (10, 1, None)
    assert (ports[1].vlans_untagged, ports[1].vlans_tagged) == ([10], [])
    assert (ports[2].vlans_untagged, ports[2].vlans_tagged) == ([1], [])
    assert (ports[3].vlans_untagged, ports[3].vlans_tagged) == ([1], [10])


def test_a_switch_without_vlans():
    ports = {1: _port(1)}
    assert model.add_vlans(ports, {}, {"1": 1}) == {}
    assert ports[1].pvid is None


async def test_sensor_and_panel_follow_the_switch(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["vlan_pvid"] = {"1": 10}
    tables["vlan_name"] = {"10": b"IoT"}
    tables["vlan_egress"] = {"10": bytes([0b11000000])}
    tables["vlan_untagged"] = {"10": bytes([0b10000000])}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    sensor = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_pvid")
    assert sensor
    assert registry.async_get(sensor).disabled
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port2_pvid")

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    switch = (await ws.receive_json())["result"]["switches"][0]
    ports = {p["n"]: p for p in switch["ports"]}
    assert switch["vlans"] == {"10": "IoT"}
    assert (ports[1]["pvid"], ports[1]["vlans_untagged"], ports[1]["vlans_tagged"]) == (
        10,
        [10],
        [],
    )
    assert (ports[2]["pvid"], ports[2]["vlans_tagged"]) == (None, [10])


async def test_the_sensor_reports_the_pvid_and_the_membership(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    from custom_components.tplink_switch_snmp.sensor import PORT_SENSORS, PortSensor

    tables["vlan_pvid"] = {"1": 10}
    tables["vlan_name"] = {"10": b"IoT"}
    tables["vlan_egress"] = {"10": bytes([0b10000000])}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    description = next(d for d in PORT_SENSORS if d.key == "pvid")
    sensor = PortSensor(entry.runtime_data, 1, description)  # off by default: build it directly
    assert sensor.native_value == 10
    assert sensor.extra_state_attributes["tagged"] == [10]
