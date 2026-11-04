"""Tests for the diagnostics download."""

import json

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp.diagnostics import async_get_config_entry_diagnostics

from .conftest import BRIDGE_MAC, MAC_OTHER, MAC_PRINTER


async def _diagnostics(hass: HomeAssistant, entry: MockConfigEntry, **update) -> dict:
    entry.add_to_hass(hass)
    if update:
        hass.config_entries.async_update_entry(entry, **update)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return await async_get_config_entry_diagnostics(hass, entry)


async def test_credentials_and_addresses_are_removed(hass: HomeAssistant, snmp, entry) -> None:
    diagnostics = await _diagnostics(hass, entry, options={"port_names": {"1": "Mein NAS"}})
    dumped = json.dumps(diagnostics)

    assert diagnostics["entry"]["data"]["host"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["community"] == "**REDACTED**"
    for secret in (
        "192.168.79.15",
        "homeassistant",
        BRIDGE_MAC,
        MAC_PRINTER,
        MAC_OTHER,
        "Mein NAS",
    ):
        assert secret not in dumped


async def test_v3_keys_and_user_are_removed(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry,
        data={
            "host": "192.168.79.15",
            "port": 161,
            "version": "3",
            "username": "geheimer-benutzer",
            "auth_protocol": "sha",
            "auth_key": "geheimer-auth-schluessel",
            "priv_protocol": "aes128",
            "priv_key": "geheimer-priv-schluessel",
        },
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    dumped = json.dumps(await async_get_config_entry_diagnostics(hass, entry))

    for secret in ("geheimer-benutzer", "geheimer-auth-schluessel", "geheimer-priv-schluessel"):
        assert secret not in dumped
    assert '"snmp_version": "3"' in dumped
    assert '"auth_protocol": "sha"' in dumped  # which algorithm is useful, the key is not


async def test_the_content_that_helps_a_bug_report(hass: HomeAssistant, snmp, entry) -> None:
    diagnostics = await _diagnostics(hass, entry)

    assert diagnostics["entry"]["snmp_version"] == "2c"
    assert diagnostics["switch"]["description"].startswith("JetStream")
    assert diagnostics["switch"]["polling_interval"] == 30
    assert diagnostics["switch"]["learned_macs"] == 2
    assert diagnostics["switch"]["last_update_success"] is True
    port = diagnostics["ports"][0]
    assert port["number"] == 1 and port["speed"] == 1000 and port["macs"] == 2
    assert [p["number"] for p in diagnostics["ports"]] == [1, 2]
