"""Tests for the storm control limits."""

from homeassistant.core import HomeAssistant

from custom_components.tplink_switch_snmp import model


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_limits_are_read_and_off_is_left_out():
    ports = {1: _port(1), 2: _port(2)}
    extras = {
        "storm_bc": {"1": 4, "2": 0},
        "storm_mc": {"1": 8},
        "storm_ul": {"1": 99, "2": 1},  # 99 is not a limit the switch knows
    }
    model.add_storm(ports, extras)

    assert ports[1].storm == {"broadcast": 1000, "multicast": 10000}
    assert ports[2].storm == {"unicast": 128}


def test_a_switch_without_the_table_has_no_limits():
    ports = {1: _port(1)}
    model.add_storm(ports, {})
    assert ports[1].storm == {}


async def test_the_panel_gets_the_limits(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["storm_bc"] = {"1": 3}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    ports = {p["n"]: p for p in (await ws.receive_json())["result"]["switches"][0]["ports"]}

    assert ports[1]["storm"] == {"broadcast": 512}
    assert ports[2]["storm"] == {}
