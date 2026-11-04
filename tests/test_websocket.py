"""Tests for the websocket commands of the panel."""

from unittest.mock import patch

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
    assert switch["model"] == "TL-SG3424"
    assert (switch["hw_version"], switch["location"], switch["contact"]) == (
        "1.0",
        "Technikraum",
        "Roberto",
    )
    assert switch["sw_version"].startswith("1.11.10")
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
    assert ports[1]["rx_discards"] == 7
    assert ports[1]["rx_pps"] is None  # the first poll has no rate yet
    assert ports[1]["link_changed_at"]  # an ISO time
    assert ports[1]["rx_util"] is None  # the first poll has no rate yet
    assert ports[2]["tx_util"] is None
    assert [m["mac"] for m in ports[1]["macs"]] == [MAC_PRINTER, MAC_OTHER]
    assert "entities" not in ports[1]  # the history no longer comes from the recorder


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

    with patch("custom_components.tplink_switch_snmp.websocket_api.vendor_of", return_value=None):
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


async def test_naming_a_port_does_not_change_the_polling(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)
    polls = snmp.walk_many.await_count

    await client.send_json_auto_id(
        {
            "type": "tplink_switch_snmp/set_port_name",
            "entry_id": entry.entry_id,
            "port": 1,
            "name": "NAS",
        }
    )
    await client.receive_json()
    await hass.async_block_till_done()

    assert snmp.walk_many.await_count == polls  # no extra poll, no reload
    assert entry.runtime_data.update_interval.total_seconds() == 30


async def test_subscribe_pushes_a_snapshot_after_each_poll(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "tplink_switch_snmp/subscribe"})
    assert (await client.receive_json())["success"]

    await entry.runtime_data.async_refresh()
    event = await client.receive_json()

    assert event["type"] == "event"
    switch = event["event"]["switches"][0]
    assert switch["entry_id"] == entry.entry_id
    assert [p["n"] for p in switch["ports"]] == [1, 2]


async def test_subscribe_also_tells_when_the_switch_goes_silent(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    from custom_components.tplink_switch_snmp.snmp import SnmpError

    await _setup(hass, entry)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "tplink_switch_snmp/subscribe"})
    await client.receive_json()

    snmp.walk_many.side_effect = SnmpError("timeout")
    await entry.runtime_data.async_refresh()
    event = await client.receive_json()

    assert event["event"]["switches"][0]["last_update_success"] is False


async def test_nothing_is_pushed_after_unsubscribing(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "tplink_switch_snmp/subscribe"})
    subscription = (await client.receive_json())["id"]

    await client.send_json_auto_id({"type": "unsubscribe_events", "subscription": subscription})
    assert (await client.receive_json())["success"]
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    await client.send_json_auto_id({"type": "ping"})
    assert (await client.receive_json())["type"] == "pong"  # no event in between


async def test_subscribe_is_for_admins_only(
    hass: HomeAssistant, hass_ws_client, hass_read_only_access_token, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass, hass_read_only_access_token)

    await client.send_json_auto_id({"type": "tplink_switch_snmp/subscribe"})
    msg = await client.receive_json()

    assert msg["success"] is False
    assert msg["error"]["code"] == "unauthorized"


async def test_history_returns_the_collected_rates(
    hass: HomeAssistant, hass_ws_client, snmp, entry, tables
) -> None:
    await _setup(hass, entry)
    tables["rx"]["1"] += 125_000_000
    await entry.runtime_data.async_refresh()
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "tplink_switch_snmp/history", "entry_id": entry.entry_id, "port": 1}
    )
    result = (await client.receive_json())["result"]

    assert result["bucket"] == 300
    assert result["end"] - result["start"] == 86400
    assert len(result["points"]) == 1
    t, rx, tx = result["points"][0]
    assert rx > 0 and t <= result["end"]


async def test_history_of_a_port_without_data(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "tplink_switch_snmp/history", "entry_id": entry.entry_id, "port": 2}
    )

    assert (await client.receive_json())["result"]["points"] == []


async def test_history_of_an_unknown_switch(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "tplink_switch_snmp/history", "entry_id": "nope", "port": 1}
    )
    msg = await client.receive_json()

    assert msg["success"] is False and msg["error"]["code"] == "not_found"


async def test_history_over_a_week_is_in_hours(
    hass: HomeAssistant, hass_ws_client, snmp, entry, tables
) -> None:
    await _setup(hass, entry)
    tables["rx"]["1"] += 125_000_000
    await entry.runtime_data.async_refresh()
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "tplink_switch_snmp/history", "entry_id": entry.entry_id, "port": 1, "range": "7d"}
    )
    result = (await client.receive_json())["result"]

    assert result["bucket"] == 3600
    assert result["end"] - result["start"] == 7 * 86400
    assert len(result["points"]) == 1


async def test_history_with_an_unknown_range_is_refused(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "tplink_switch_snmp/history", "entry_id": entry.entry_id, "port": 1, "range": "1y"}
    )
    msg = await client.receive_json()

    assert msg["success"] is False and msg["error"]["code"] == "invalid_format"
