"""Tests for the websocket commands of the panel."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import BRIDGE_MAC, MAC_OTHER, MAC_PRINTER


async def _snapshot(client) -> dict:
    await client.send_json_auto_id({"type": "tplink_switch_snmp/snapshot"})
    msg = await client.receive_json()
    assert msg["success"], msg
    return msg["result"]["switches"][0]


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_snapshot_describes_the_switch(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    switch = await _snapshot(await hass_ws_client(hass))

    assert switch["entry_id"] == entry.entry_id
    assert switch["title"] == "TL-SG3424"
    assert switch["host"] == "192.168.79.15"
    assert switch["mac"] == BRIDGE_MAC
    assert switch["manufacturer"] == "TP-Link"
    assert switch["model"] == "JetStream 24-Port Gigabit L2 Managed Switch"
    assert switch["uptime"] == 158 * 86400
    assert switch["interval"] == 30
    assert switch["last_update_success"] is True
    assert [p["n"] for p in switch["ports"]] == [1, 2]


async def test_snapshot_port_values(hass: HomeAssistant, hass_ws_client, snmp, entry) -> None:
    await _setup(hass, entry)
    ports = {p["n"]: p for p in (await _snapshot(await hass_ws_client(hass)))["ports"]}

    assert ports[1]["up"] is True and ports[1]["speed"] == 1000
    assert ports[2]["up"] is False and ports[2]["speed"] == 0
    assert ports[1]["tx_errors"] == 3
    assert [m["mac"] for m in ports[1]["macs"]] == [MAC_PRINTER, MAC_OTHER]
    # The rate sensors are the ones the panel draws the history from.
    assert ports[1]["entities"]["rx_rate"].startswith("sensor.")
    assert ports[1]["entities"]["tx_rate"].startswith("sensor.")


async def test_device_names_come_from_the_device_registry(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    other = MockConfigEntry(domain="test", data={})
    other.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, MAC_PRINTER)},
        name="Drucker HP",
        manufacturer="Hewlett Packard",
    )

    ports = {p["n"]: p for p in (await _snapshot(await hass_ws_client(hass)))["ports"]}
    named, unknown = ports[1]["macs"]

    assert named == {"mac": MAC_PRINTER, "name": "Drucker HP", "manufacturer": "Hewlett Packard"}
    assert unknown == {"mac": MAC_OTHER, "name": None, "manufacturer": None}


async def test_set_and_clear_a_port_name(hass: HomeAssistant, hass_ws_client, snmp, entry) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "tplink_switch_snmp/set_port_name",
            "entry_id": entry.entry_id,
            "port": 1,
            "name": "  NAS  ",
        }
    )
    assert (await client.receive_json())["result"] == {"name": "NAS"}
    assert entry.options["port_names"] == {"1": "NAS"}
    assert (await _snapshot(client))["ports"][0]["name"] == "NAS"

    await client.send_json_auto_id(
        {
            "type": "tplink_switch_snmp/set_port_name",
            "entry_id": entry.entry_id,
            "port": 1,
            "name": "",
        }
    )
    assert (await client.receive_json())["success"]
    assert entry.options["port_names"] == {}
    assert (await _snapshot(client))["ports"][0]["name"] == ""


async def test_port_name_is_limited_in_length(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "tplink_switch_snmp/set_port_name",
            "entry_id": entry.entry_id,
            "port": 1,
            "name": "x" * 41,
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is False
    assert msg["error"]["code"] == "invalid_format"


async def test_unknown_switch(hass: HomeAssistant, hass_ws_client, snmp, entry) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "tplink_switch_snmp/set_port_name", "entry_id": "nope", "port": 1, "name": "x"}
    )
    msg = await client.receive_json()

    assert msg["success"] is False
    assert msg["error"]["code"] == "not_found"


async def test_commands_are_for_admins_only(
    hass: HomeAssistant, hass_ws_client, hass_read_only_access_token, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass, hass_read_only_access_token)

    await client.send_json_auto_id({"type": "tplink_switch_snmp/snapshot"})
    msg = await client.receive_json()

    assert msg["success"] is False
    assert msg["error"]["code"] == "unauthorized"
