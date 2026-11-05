"""Tests for how the ports are set at the switch (TP-Link's port configuration table)."""

from homeassistant.core import HomeAssistant

from custom_components.tplink_switch_snmp import model


def _port(number: int) -> model.PortData:
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_the_configuration_is_filled_in():
    ports = {1: _port(1), 2: _port(2), 3: _port(3), 4: _port(4)}
    extras = {
        "cfg_mode": {"1": 6, "2": 4, "3": 99},
        "cfg_flow": {"1": 0, "2": 1},
        "cfg_lag": {"1": b"", "2": b"LAG1", "3": b"--", "4": b"N/A"},
    }
    model.add_config(ports, extras)

    assert [p.mode for p in ports.values()] == ["auto", "100full", None, None]  # 99 is unknown
    assert [p.flow_control for p in ports.values()] == [False, True, None, None]
    assert [p.lag for p in ports.values()] == [None, "LAG1", None, None]


def test_a_switch_without_the_table_leaves_everything_unknown():
    ports = {1: _port(1)}
    model.add_config(ports, {})
    assert (ports[1].mode, ports[1].flow_control, ports[1].lag) == (None, None, None)


async def test_the_panel_gets_the_configuration(
    hass: HomeAssistant, snmp, entry, tables, hass_ws_client
) -> None:
    tables["cfg_mode"] = {"1": 4, "2": 6}
    tables["cfg_flow"] = {"1": 1, "2": 0}
    tables["cfg_lag"] = {"1": b"LAG2", "2": b""}
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tplink_switch_snmp/snapshot"})
    ports = {p["n"]: p for p in (await ws.receive_json())["result"]["switches"][0]["ports"]}

    assert ports[1]["mode"] == "100full"
    assert ports[1]["flow_control"] is True
    assert ports[1]["lag"] == "LAG2"
    assert ports[2]["mode"] == "auto"
    assert ports[2]["lag"] is None
