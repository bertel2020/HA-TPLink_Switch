"""Tests for the port sensor on known devices and the move event."""

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.tplink_switch_snmp import logbook
from custom_components.tplink_switch_snmp.const import DOMAIN, EVENT_DEVICE_MOVED

from .conftest import BRIDGE_MAC, MAC_OTHER, MAC_PRINTER


def _known_device(hass: HomeAssistant, mac: str, name: str) -> dr.DeviceEntry:
    other = MockConfigEntry(domain="test", data={})
    other.add_to_hass(hass)
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        name=name,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _sensor(hass: HomeAssistant, mac: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{BRIDGE_MAC}_device_{mac}_port"
    )


async def test_only_known_devices_get_a_port_sensor(hass: HomeAssistant, snmp, entry) -> None:
    _known_device(hass, MAC_PRINTER, "Drucker")
    await _setup(hass, entry)

    entity_id = _sensor(hass, MAC_PRINTER)
    assert entity_id
    assert hass.states.get(entity_id).state == "1"
    assert _sensor(hass, MAC_OTHER) is None  # Home Assistant does not know this one


async def test_the_sensor_belongs_to_the_switch_and_is_named_after_the_device(
    hass: HomeAssistant, snmp, entry
) -> None:
    _known_device(hass, MAC_PRINTER, "Drucker")
    await _setup(hass, entry)

    sensor = er.async_get(hass).async_get(_sensor(hass, MAC_PRINTER))
    switch = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, BRIDGE_MAC), entry.entry_id)
    assert sensor.device_id == switch.id
    assert "Drucker" in hass.states.get(sensor.entity_id).attributes["friendly_name"]


async def test_port_name_is_an_attribute(hass: HomeAssistant, snmp, entry) -> None:
    _known_device(hass, MAC_PRINTER, "Drucker")
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"port_names": {"1": "Büro"}})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    attributes = hass.states.get(_sensor(hass, MAC_PRINTER)).attributes
    assert attributes["port_name"] == "Büro"
    assert attributes["mac"] == MAC_PRINTER
    assert attributes["device_name"] == "Drucker"


async def test_state_is_unknown_when_the_device_is_gone(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    _known_device(hass, MAC_PRINTER, "Drucker")
    await _setup(hass, entry)

    tables["fdb_q"].pop("1.0.4.32.249.54.2")  # aged out of the switch's table
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(_sensor(hass, MAC_PRINTER)).state == "unknown"


async def test_a_device_that_appears_later_gets_its_sensor(
    hass: HomeAssistant, snmp, entry
) -> None:
    await _setup(hass, entry)
    assert _sensor(hass, MAC_PRINTER) is None

    _known_device(hass, MAC_PRINTER, "Drucker")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert _sensor(hass, MAC_PRINTER)


async def test_event_when_a_known_device_changes_port(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    device = _known_device(hass, MAC_PRINTER, "Drucker")
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_DEVICE_MOVED)

    tables["fdb_q"]["1.0.4.32.249.54.2"] = 2  # now on bridge port 2
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert len(events) == 1
    data = events[0].data
    assert data["mac"] == MAC_PRINTER and data["name"] == "Drucker"
    assert (data["from_port"], data["to_port"]) == (1, 2)
    assert data["device_id"] == device.id
    assert hass.states.get(_sensor(hass, MAC_PRINTER)).state == "2"


async def test_no_event_for_unknown_devices_or_without_a_move(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    _known_device(hass, MAC_PRINTER, "Drucker")
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_DEVICE_MOVED)

    tables["fdb_q"]["1.0.8.220.84.149.70"] = 2  # an unknown device moves
    await entry.runtime_data.async_refresh()  # the known one stays
    await hass.async_block_till_done()

    assert events == []


async def test_a_new_device_is_not_a_move(hass: HomeAssistant, snmp, entry, tables) -> None:
    _known_device(hass, MAC_PRINTER, "Drucker")
    tables["fdb_q"].pop("1.0.4.32.249.54.2")
    await _setup(hass, entry)
    events = async_capture_events(hass, EVENT_DEVICE_MOVED)

    tables["fdb_q"]["1.0.4.32.249.54.2"] = 2  # it was not in the table before
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert events == []


async def test_logbook_text(hass: HomeAssistant) -> None:
    described = {}

    @callback
    def register(domain, event_type, describe):
        described[event_type] = describe

    logbook.async_describe_events(hass, register)
    data = {
        "switch": "TL-SG3424",
        "mac": MAC_PRINTER,
        "name": "Drucker",
        "from_port": 1,
        "from_port_name": "",
        "to_port": 12,
        "to_port_name": "AP",
    }
    result = described[EVENT_DEVICE_MOVED](Event(EVENT_DEVICE_MOVED, data))

    assert result["name"] == "Drucker"
    assert result["message"] == "moved from Port 1 to Port 12 (AP) at TL-SG3424"
