"""Tests for link change events, the timestamp and the logbook text."""

from datetime import timedelta

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.tplink_switch_snmp import logbook
from custom_components.tplink_switch_snmp.const import (
    DOMAIN,
    EVENT_ALARM,
    EVENT_LINK_CHANGED,
    OID_SYS_UPTIME,
)

from .conftest import BRIDGE_MAC, SYSTEM


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _uptime(snmp, ticks: int) -> None:
    system = {**SYSTEM, OID_SYS_UPTIME: ticks}
    snmp.get.side_effect = lambda *oids: {o: system[o] for o in oids if o in system}


async def test_first_poll_fires_nothing(hass: HomeAssistant, snmp, entry) -> None:
    events = async_capture_events(hass, EVENT_LINK_CHANGED)
    await _setup(hass, entry)
    assert events == []


async def test_event_when_the_link_goes_down(hass: HomeAssistant, snmp, entry, tables) -> None:
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_LINK_CHANGED)

    tables["oper"]["1"] = 2  # down
    tables["last_change"]["1"] = SYSTEM[OID_SYS_UPTIME] + 100
    _uptime(snmp, SYSTEM[OID_SYS_UPTIME] + 200)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert len(events) == 1
    data = events[0].data
    assert data["port"] == 1 and data["up"] is False and data["flap"] is False
    assert data["entry_id"] == entry.entry_id and data["switch"] == "TL-SG3424"
    link = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{BRIDGE_MAC}_port1_link"
    )
    assert data["entity_id"] == link


async def test_flap_between_two_polls(hass: HomeAssistant, snmp, entry, tables) -> None:
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_LINK_CHANGED)

    tables["last_change"]["1"] = SYSTEM[OID_SYS_UPTIME] + 100  # still up, but it changed
    _uptime(snmp, SYSTEM[OID_SYS_UPTIME] + 200)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["up"] is True and events[0].data["flap"] is True
    assert entry.runtime_data.data.ports[1].link_changes == 2  # down and up again


async def test_unchanged_ports_fire_nothing(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_LINK_CHANGED)

    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert events == []


async def test_a_reboot_does_not_flood_the_log(hass: HomeAssistant, snmp, entry, tables) -> None:
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_LINK_CHANGED)

    tables["last_change"] = {"1": 300, "2": 400, "25": 0}  # everything is new after a reboot
    _uptime(snmp, 6000)  # uptime fell from 158 days to a minute
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert events == []


async def test_the_port_name_is_part_of_the_event(hass: HomeAssistant, snmp, entry, tables) -> None:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"port_names": {"1": "NAS"}})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    events = async_capture_events(hass, EVENT_LINK_CHANGED)

    tables["oper"]["1"] = 2
    tables["last_change"]["1"] = SYSTEM[OID_SYS_UPTIME] + 100
    _uptime(snmp, SYSTEM[OID_SYS_UPTIME] + 200)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert events[0].data["port_name"] == "NAS"


async def test_link_change_time_is_stable(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    first = entry.runtime_data.data.ports[1].link_changed_at
    assert first is not None
    # ifLastChange is 1000 ticks, the uptime 158 days: the change was long ago
    assert first < dt_util.utcnow() - timedelta(days=157)

    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.data.ports[1].link_changed_at == first  # does not drift


async def test_link_changed_sensor_is_opt_in(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_MAC}_port1_link_changed")

    assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_logbook_texts(hass: HomeAssistant) -> None:
    described = {}

    @callback
    def register(domain, event_type, describe):
        described[event_type] = describe

    logbook.async_describe_events(hass, register)
    describe = described[EVENT_LINK_CHANGED]
    base = {
        "switch": "TL-SG3424",
        "port": 12,
        "port_name": "AP",
        "speed": 1000,
        "entity_id": "binary_sensor.x",
    }

    up = describe(Event(EVENT_LINK_CHANGED, {**base, "up": True, "flap": False}))
    assert up["message"] == "Port 12 (AP): link up at 1 Gbit/s"
    assert up["name"] == "TL-SG3424" and up["entity_id"] == "binary_sensor.x"
    assert (
        describe(Event(EVENT_LINK_CHANGED, {**base, "up": False, "flap": False}))["message"]
        == "Port 12 (AP): link down"
    )
    assert (
        "came back"
        in describe(Event(EVENT_LINK_CHANGED, {**base, "up": True, "flap": True}))["message"]
    )
    nameless = {**base, "port_name": "", "speed": 100}
    assert (
        describe(Event(EVENT_LINK_CHANGED, {**nameless, "up": True, "flap": False}))["message"]
        == "Port 12: link up at 100 Mbit/s"
    )


async def test_logbook_text_of_alarms(hass: HomeAssistant) -> None:
    described = {}

    @callback
    def register(domain, event_type, describe):
        described[event_type] = describe

    logbook.async_describe_events(hass, register)
    describe = described[EVENT_ALARM]

    cpu = describe(Event(EVENT_ALARM, {"switch": "TL-SG3424", "alarm": "cpu_load"}))
    assert cpu["name"] == "TL-SG3424"
    assert cpu["message"] == "CPU load is over 80 %"
    assert describe(Event(EVENT_ALARM, {"alarm": "other"}))["message"] == "other"
