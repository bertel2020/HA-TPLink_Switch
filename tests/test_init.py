"""Tests for setup, the entities and unload."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp.const import DOMAIN, OID_SYS_OBJECT_ID
from custom_components.tplink_switch_snmp.snmp import SnmpError

from .conftest import BRIDGE_MAC, MAC_OTHER, MAC_PRINTER, SYSTEM


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{BRIDGE_MAC}_{key}")
    assert entity_id, key
    return entity_id


async def test_setup_creates_port_entities(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get(_entity(hass, "binary_sensor", "port1_link")).state == "on"
    assert hass.states.get(_entity(hass, "binary_sensor", "port2_link")).state == "off"
    assert hass.states.get(_entity(hass, "sensor", "port1_speed")).state == "1000"
    assert hass.states.get(_entity(hass, "sensor", "port2_speed")).state == "0"


async def test_only_physical_ports_get_entities(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    unique_ids = {
        e.unique_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }

    assert f"{BRIDGE_MAC}_port1_link" in unique_ids
    assert not any("port25" in u for u in unique_ids)


async def test_uptime_and_mac_count(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)

    uptime = hass.states.get(_entity(hass, "sensor", "uptime"))
    assert float(uptime.state) == 158.0  # shown in days
    macs = hass.states.get(_entity(hass, "sensor", "port1_macs"))
    assert macs.state == "2"
    assert macs.attributes["mac_addresses"] == [MAC_PRINTER, MAC_OTHER]


async def test_rates_follow_the_counters(hass: HomeAssistant, snmp, entry, tables) -> None:
    await _setup(hass, entry)
    # The first poll has nothing to compare with.
    assert hass.states.get(_entity(hass, "sensor", "port1_rx_rate")).state == "unknown"

    tables["rx"]["1"] += 125_000_000
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert float(hass.states.get(_entity(hass, "sensor", "port1_rx_rate")).state) > 0


async def test_noisy_entities_are_off_by_default(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    registry = er.async_get(hass)

    for key in ("port1_rx_total", "port1_tx_errors"):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_{key}")
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_entities_become_unavailable_when_the_switch_is_silent(
    hass: HomeAssistant, snmp, entry
) -> None:
    await _setup(hass, entry)
    snmp.walk_many.side_effect = SnmpError("timeout")

    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(_entity(hass, "binary_sensor", "port1_link")).state == "unavailable"


async def test_setup_is_retried_when_the_switch_is_not_there(
    hass: HomeAssistant, snmp, entry
) -> None:
    snmp.walk_many.side_effect = SnmpError("timeout")
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_releases_the_client(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    snmp.close.assert_called_once()


async def test_device_info_comes_from_the_switch(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, BRIDGE_MAC), entry.entry_id)
    assert device.manufacturer == "TP-Link"
    assert device.model == "JetStream 24-Port Gigabit L2 Managed Switch"


async def test_unknown_maker_is_left_empty(hass: HomeAssistant, snmp, entry) -> None:
    system = {**SYSTEM, OID_SYS_OBJECT_ID: "1.3.6.1.4.1.9.1.1"}
    snmp.get.side_effect = lambda *oids: {o: system[o] for o in oids if o in system}
    await _setup(hass, entry)

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, BRIDGE_MAC), entry.entry_id)
    assert device.manufacturer is None
