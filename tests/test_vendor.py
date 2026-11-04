"""Tests for the manufacturer lookup by MAC address."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp import vendor

from .conftest import MAC_OTHER, MAC_PRINTER


def test_private_addresses_are_recognised() -> None:
    assert vendor.is_private_mac("02:42:ac:11:00:02")  # locally administered
    assert vendor.is_private_mac("da:a1:19:00:00:01")
    assert not vendor.is_private_mac("00:04:20:f9:36:02")
    assert not vendor.is_private_mac("3c:a6:2f:12:ab:01")
    assert not vendor.is_private_mac("not a mac")


def test_a_private_address_has_no_manufacturer() -> None:
    with (
        patch.object(vendor.aiooui, "is_loaded", return_value=True),
        patch.object(vendor.aiooui, "get_vendor", return_value="Acme") as get,
    ):
        assert vendor.vendor_of("02:42:ac:11:00:02") is None
        get.assert_not_called()
        assert vendor.vendor_of("00:04:20:f9:36:02") == "Acme"


def test_nothing_is_looked_up_before_the_list_is_loaded() -> None:
    with patch.object(vendor.aiooui, "is_loaded", return_value=False):
        assert vendor.vendor_of("00:04:20:f9:36:02") is None


async def test_the_list_is_loaded_once() -> None:
    with (
        patch.object(vendor.aiooui, "is_loaded", side_effect=[False, True]),
        patch.object(vendor.aiooui, "async_load") as load,
    ):
        await vendor.async_load()
        await vendor.async_load()
    load.assert_awaited_once()


async def _snapshot_macs(hass, hass_ws_client, entry) -> dict[str, dict]:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "tplink_switch_snmp/snapshot"})
    ports = (await client.receive_json())["result"]["switches"][0]["ports"]
    return {m["mac"]: m for m in ports[0]["macs"]}


async def test_the_panel_gets_the_manufacturer_from_the_address(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    with patch("custom_components.tplink_switch_snmp.websocket_api.vendor_of", return_value="Acme"):
        macs = await _snapshot_macs(hass, hass_ws_client, entry)

    assert macs[MAC_PRINTER] == {"mac": MAC_PRINTER, "name": None, "manufacturer": "Acme"}


async def test_a_manufacturer_known_to_home_assistant_wins(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    other = MockConfigEntry(domain="test", data={})
    other.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, MAC_PRINTER)},
        name="Drucker",
        manufacturer="Hewlett Packard",
    )
    with patch("custom_components.tplink_switch_snmp.websocket_api.vendor_of", return_value="Acme"):
        macs = await _snapshot_macs(hass, hass_ws_client, entry)

    assert macs[MAC_PRINTER]["manufacturer"] == "Hewlett Packard"
    assert macs[MAC_OTHER]["manufacturer"] == "Acme"  # no device: from the address
