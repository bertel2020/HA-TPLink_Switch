"""Tests for port mirroring and port isolation."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.tplink_switch_snmp import model
from custom_components.tplink_switch_snmp.const import DOMAIN

from .conftest import BRIDGE_MAC


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def _ports(count: int = 4) -> dict[int, model.PortData]:
    return {n: _port(n) for n in range(1, count + 1)}


def test_a_port_list_is_read_in_every_style():
    assert model.port_list(b"1-3,7,9-10") == {1, 2, 3, 7, 9, 10}
    assert model.port_list(b"1/0/1-1/0/3, 1/0/8") == {1, 2, 3, 8}
    assert model.port_list(b"") == set()
    assert model.port_list(b"5-2,x,0-3,1-999") == set()  # backwards, no number, no ports, too long


def test_mirroring_marks_the_monitor_and_the_sources():
    ports = _ports()
    extras = {
        "mirror_state": {"1": 1, "2": 0},
        "mirror_monitor": {"1": 4, "2": 3},
        "mirror_in": {"1": b"1-2", "2": b"3"},
        "mirror_out": {"1": b"2"},
    }
    groups = model.add_mirror(ports, extras)

    assert groups == [{"group": "1", "monitor": 4, "ingress": [1, 2], "egress": [2]}]
    assert [p.mirror for p in ports.values()] == ["source", "source", None, "monitor"]


def test_the_monitor_port_may_come_as_text_and_may_be_no_port():
    ports = _ports(2)
    groups = model.add_mirror(ports, {"mirror_state": {"1": 1}, "mirror_monitor": {"1": b"1/0/2"}})
    assert groups[0]["monitor"] == 2
    assert ports[2].mirror == "monitor"

    ports = _ports(2)
    model.add_mirror(ports, {"mirror_state": {"1": 1}, "mirror_monitor": {"1": 99}})
    assert [p.mirror for p in ports.values()] == [None, None]


def test_a_port_that_cannot_reach_all_the_others_is_isolated():
    ports = _ports(3)
    model.add_isolation(ports, {"isolation": {"1": b"1-3", "2": b"3", "3": b"", "9": b"1"}})

    assert (ports[1].isolated, ports[1].isolation_forward) == (False, [1, 2, 3])
    assert (ports[2].isolated, ports[2].isolation_forward) == (True, [3])
    assert (ports[3].isolated, ports[3].isolation_forward) == (None, None)  # empty: not set


async def test_the_sensor_the_panel_and_the_ports_follow_the_switch(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["mirror_state"] = {"1": 1}
    tables["mirror_monitor"] = {"1": 2}
    tables["mirror_in"] = {"1": b"1"}
    tables["isolation"] = {"1": b"1", "2": b"1-2"}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    sensor = registry.async_get_entity_id("binary_sensor", DOMAIN, f"{BRIDGE_MAC}_feature_mirror")
    assert sensor

    from custom_components.tplink_switch_snmp.binary_sensor import SwitchFeature

    feature = SwitchFeature(entry.runtime_data, "mirror")
    assert feature.is_on is True
    assert feature.extra_state_attributes == {
        "groups": [{"group": "1", "monitor": 2, "ingress": [1], "egress": []}]
    }
    assert SwitchFeature(entry.runtime_data, "dos").extra_state_attributes is None

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    switch = (await ws.receive_json())["result"]["switches"][0]
    ports = {p["n"]: p for p in switch["ports"]}
    assert switch["features"]["mirror"] is True
    assert switch["mirror"][0]["monitor"] == 2
    assert (ports[1]["mirror"], ports[2]["mirror"]) == ("source", "monitor")
    assert (ports[1]["isolated"], ports[2]["isolated"]) == (True, False)
