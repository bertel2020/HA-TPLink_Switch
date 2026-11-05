"""Tests for the loop detection of TP-Link's own tables."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.tplink_switch_snmp import model
from custom_components.tplink_switch_snmp.const import (
    DOMAIN,
    OID_LOOP_LOOPED,
    OID_SYS_OBJECT_ID,
)
from custom_components.tplink_switch_snmp.snmp import SnmpError

from .conftest import BRIDGE_MAC, SYSTEM


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _sensor(hass: HomeAssistant, number: int) -> str | None:
    return er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{BRIDGE_MAC}_port{number}_loop"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, True),
        (0, False),
        (b"Loop", True),
        (b"No Loop", False),
        (b"Normal", False),
        (b"", False),
        (b"0", False),
        (b"Blocked", True),
        (b"Not Blocked", False),
    ],
)
def test_flag(value, expected):
    assert model.flag(value) is expected


def _ports():
    return {1: _port(1), 2: _port(2)}


def _port(number):
    return model.PortData(number, number, f"port {number}", True, 1000, 0, 0, 0, 0)


def test_loops_are_filled_in_for_watched_ports_only():
    ports = _ports()
    extras = {
        "loop_on": {"1": 1, "2": 0},
        "loop": {"1": b"Loop", "2": b"Loop"},
        "loop_blocked": {"1": b"Not Blocked"},
    }
    model.add_loops(ports, extras)
    assert ports[1].loop is True
    assert ports[1].loop_blocked is False
    assert ports[2].loop is None  # detection is off there


def test_loops_without_the_enabled_column_and_without_ports():
    ports = _ports()
    model.add_loops(ports, {"loop": {"1": b"No Loop"}})
    assert ports[1].loop is False
    assert ports[1].loop_blocked is None
    assert ports[2].loop is None
    model.add_loops(ports, {})  # a switch without the table


async def test_loop_sensor_follows_the_switch(hass: HomeAssistant, snmp, entry, tables) -> None:
    tables["loop_on"] = {"1": 1, "2": 1}
    tables["loop"] = {"1": b"No Loop", "2": b"Loop"}
    tables["loop_blocked"] = {"1": b"Not Blocked", "2": b"Blocked"}
    await _setup(hass, entry)

    assert hass.states.get(_sensor(hass, 1)).state == "off"
    looped = hass.states.get(_sensor(hass, 2))
    assert looped.state == "on"
    assert looped.attributes["blocked"] is True
    assert looped.attributes["port"] == 2


async def test_no_loop_sensor_without_the_table(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert _sensor(hass, 1) is None


async def test_a_switch_that_refuses_the_table_is_still_polled(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    original = snmp.walk_many.side_effect

    def walk_many(oids):
        if OID_LOOP_LOOPED in oids.values():
            raise SnmpError("noSuchName")  # SNMPv1 refuses a table that does not exist
        return original(oids)

    tables["loop"] = {"1": b"Loop"}
    snmp.walk_many.side_effect = walk_many
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert _sensor(hass, 1) is None


async def test_another_error_in_the_table_is_not_hidden(hass: HomeAssistant, snmp, entry) -> None:
    original = snmp.walk_many.side_effect

    def walk_many(oids):
        if OID_LOOP_LOOPED in oids.values():
            raise RuntimeError("bug")
        return original(oids)

    snmp.walk_many.side_effect = walk_many
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_other_makers_are_not_asked_for_the_table(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["loop"] = {"1": b"Loop"}
    original = snmp.get.side_effect

    def get(*oids):
        result = original(*oids)
        if OID_SYS_OBJECT_ID in oids:
            result[OID_SYS_OBJECT_ID] = "1.3.6.1.4.1.9.1.1"
        return result

    snmp.get.side_effect = get
    assert SYSTEM[OID_SYS_OBJECT_ID].startswith("1.3.6.1.4.1.11863")
    await _setup(hass, entry)

    assert _sensor(hass, 1) is None
