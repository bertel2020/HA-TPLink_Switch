"""Tests for setup, the entities and unload."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp.const import (
    DOMAIN,
    OID_SYS_DESCR,
    OID_SYS_OBJECT_ID,
    OID_SYS_UPTIME,
)
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
    assert device.model == "TL-SG3424"
    assert device.hw_version == "1.0"
    assert device.sw_version == "1.11.10 Build 20150713 Rel.53496(n)"


async def test_unknown_maker_is_left_empty(hass: HomeAssistant, snmp, entry) -> None:
    system = {**SYSTEM, OID_SYS_OBJECT_ID: "1.3.6.1.4.1.9.1.1"}
    snmp.get.side_effect = lambda *oids: {o: system[o] for o in oids if o in system}
    await _setup(hass, entry)

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, BRIDGE_MAC), entry.entry_id)
    assert device.manufacturer is None


async def test_uptime_keeps_counting_after_the_counter_wraps(
    hass: HomeAssistant, snmp, entry
) -> None:
    near_limit = {**SYSTEM, OID_SYS_UPTIME: 2**32 - 1000}
    snmp.get.side_effect = lambda *oids: {o: near_limit[o] for o in oids if o in near_limit}
    await _setup(hass, entry)
    before = entry.runtime_data.data.uptime

    wrapped = {**SYSTEM, OID_SYS_UPTIME: 2000}
    snmp.get.side_effect = lambda *oids: {o: wrapped[o] for o in oids if o in wrapped}
    await entry.runtime_data.async_refresh()

    assert entry.runtime_data.data.uptime == (2**32 + 2000) // 100
    assert entry.runtime_data.data.uptime > before


async def test_v1_reads_the_32_bit_counters(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, data={**entry.data, "version": "1"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    asked = snmp.walk_many.await_args_list[0].args[0]
    assert asked["rx"].endswith("2.2.1.10")  # ifInOctets, not the 64 bit ifHCInOctets


async def test_discards_and_utilization_sensors(hass: HomeAssistant, snmp, entry, tables) -> None:
    await _setup(hass, entry)
    registry = er.async_get(hass)
    for key in ("port1_rx_discards", "port1_rx_utilization"):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_{key}")
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION

    data = entry.runtime_data.data
    assert data.ports[1].rx_discards == 7
    tables["rx"]["1"] += 125_000_000
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.data.ports[1].rx_util is not None


async def test_model_falls_back_to_the_description_for_other_makers(
    hass: HomeAssistant, snmp, entry
) -> None:
    system = {**SYSTEM, OID_SYS_OBJECT_ID: "1.3.6.1.4.1.9.1.1"}
    snmp.get.side_effect = lambda *oids: {o: system[o] for o in oids if o in system}
    await _setup(hass, entry)

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, BRIDGE_MAC), entry.entry_id)
    assert device.model == "JetStream 24-Port Gigabit L2 Managed Switch"
    assert device.sw_version is None
    snmp.get.assert_any_await("1.3.6.1.2.1.1.6.0")  # the standard location is still asked for
    asked = [c.args[0] for c in snmp.get.await_args_list if len(c.args) == 1]
    assert not any(oid.startswith("1.3.6.1.4.1.11863") for oid in asked)


async def test_the_entity_mib_names_maker_model_and_versions(
    hass: HomeAssistant, snmp, entry
) -> None:
    system = {
        **SYSTEM,
        OID_SYS_OBJECT_ID: "1.3.6.1.4.1.9.1.1",
        "1.3.6.1.2.1.47.1.1.1.1.12.1": b"ACME",
        "1.3.6.1.2.1.47.1.1.1.1.13.1": b"AS-24",
        "1.3.6.1.2.1.47.1.1.1.1.8.1": b"2.0",
        "1.3.6.1.2.1.47.1.1.1.1.10.1": b"5.4.3",
    }
    snmp.get.side_effect = lambda *oids: {o: system[o] for o in oids if o in system}
    await _setup(hass, entry)

    data = entry.runtime_data.data
    assert data.manufacturer == "ACME"
    assert (data.model, data.hw_version, data.sw_version) == ("AS-24", "2.0", "5.4.3")


async def test_a_jetstream_description_names_tplink_without_the_object_id(
    hass: HomeAssistant, snmp, entry
) -> None:
    system = {
        **SYSTEM,
        OID_SYS_OBJECT_ID: "1.3.6.1.4.1.1.1",
        OID_SYS_DESCR: b"JetStream 24-Port Gigabit L2 Managed Switch",
    }
    snmp.get.side_effect = lambda *oids: {o: system[o] for o in oids if o in system}
    await _setup(hass, entry)

    data = entry.runtime_data.data
    assert data.manufacturer == "TP-Link"


async def test_an_unknown_private_value_does_not_stop_the_poll(
    hass: HomeAssistant, snmp, entry
) -> None:

    original = snmp.get.side_effect

    def get(*oids):
        if len(oids) == 1 and oids[0].startswith("1.3.6.1.4.1.11863"):
            raise SnmpError("noSuchName")  # SNMPv1 refuses a value that does not exist
        return original(*oids)

    snmp.get.side_effect = get
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.data.model is None
    assert entry.runtime_data.data.location == "Technikraum"


async def test_the_info_is_read_only_once(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    asked = len([c for c in snmp.get.await_args_list if len(c.args) == 1])

    await entry.runtime_data.async_refresh()

    assert len([c for c in snmp.get.await_args_list if len(c.args) == 1]) == asked


async def test_packet_sensors_are_off_by_default_and_follow_the_counters(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    await _setup(hass, entry)
    registry = er.async_get(hass)
    for key in ("port1_rx_packets", "port1_tx_packets", "port1_rx_broadcast", "port1_rx_multicast"):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_{key}")
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION

    tables["rx_bc"]["1"] += 5000
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.data.ports[1].rx_bcast_pps > 0
    assert entry.runtime_data.data.ports[1].rx_pps >= entry.runtime_data.data.ports[1].rx_bcast_pps


async def test_v1_reads_the_32_bit_packet_counters(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, data={**entry.data, "version": "1"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    asked = snmp.walk_many.await_args_list[0].args[0]
    assert asked["rx_uc"].endswith("2.2.1.11")  # ifInUcastPkts
    assert asked["rx_bc"].endswith("31.1.1.1.3")  # ifInBroadcastPkts, 32 bit


async def test_port_entities_carry_their_port_number(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)

    assert hass.states.get(_entity(hass, "binary_sensor", "port2_link")).attributes["port"] == 2
    assert hass.states.get(_entity(hass, "sensor", "port1_speed")).attributes["port"] == 1
    macs = hass.states.get(_entity(hass, "sensor", "port1_macs"))
    assert macs.attributes["port"] == 1 and macs.attributes["mac_addresses"]
