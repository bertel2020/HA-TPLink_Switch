"""Tests for port security (the most MAC addresses a port may learn)."""

from homeassistant.core import HomeAssistant

from custom_components.tplink_switch_snmp import model


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_only_ports_with_port_security_on_get_values():
    ports = {1: _port(1), 2: _port(2), 3: _port(3)}
    extras = {
        "sec_on": {"1": 1, "2": 0, "3": 1},
        "sec_max": {"1": 5, "2": 5, "3": 8},
        "sec_learned": {"1": 5, "2": 2},
    }
    model.add_security(ports, extras)

    assert (ports[1].security_max, ports[1].security_learned) == (5, 5)
    assert (ports[2].security_max, ports[2].security_learned) == (None, None)
    assert (ports[3].security_max, ports[3].security_learned) == (8, None)


def test_a_switch_without_the_table_has_no_port_security():
    ports = {1: _port(1)}
    model.add_security(ports, {})
    assert ports[1].security_max is None


async def test_the_panel_gets_port_security(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["sec_on"] = {"1": 1}
    tables["sec_max"] = {"1": 4}
    tables["sec_learned"] = {"1": 4}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    ports = {p["n"]: p for p in (await ws.receive_json())["result"]["switches"][0]["ports"]}

    assert (ports[1]["security_max"], ports[1]["security_learned"]) == (4, 4)
    assert ports[2]["security_max"] is None
