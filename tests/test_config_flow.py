"""Tests for the config flow."""

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tplink_switch_snmp.const import DOMAIN, OID_BRIDGE_ADDRESS, OID_SYS_NAME
from custom_components.tplink_switch_snmp.snmp import SnmpError

from .conftest import BRIDGE_MAC, SYSTEM

USER_INPUT = {"host": "192.168.79.15", "community": "homeassistant", "port": 161}


async def _start(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})


async def test_user_flow_creates_entry(hass: HomeAssistant, snmp) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "TL-SG3424"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == BRIDGE_MAC


async def test_switch_that_does_not_answer(hass: HomeAssistant, snmp) -> None:
    snmp.get.side_effect = SnmpError("timeout")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_device_without_bridge_address_is_refused(hass: HomeAssistant, snmp) -> None:
    snmp.get.side_effect = lambda *oids: {}
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["errors"] == {"base": "cannot_connect"}


async def test_error_can_be_corrected(hass: HomeAssistant, snmp) -> None:
    good = snmp.get.side_effect
    snmp.get.side_effect = SnmpError("timeout")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"]

    snmp.get.side_effect = good
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_same_switch_twice_updates_the_address(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, "host": "192.168.79.99"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == "192.168.79.99"


def test_flow_is_registered() -> None:
    assert config_entries.HANDLERS.get(DOMAIN) is not None


async def _reconfigure(hass: HomeAssistant, entry) -> dict:
    return await entry.start_reconfigure_flow(hass)


async def test_reconfigure_changes_the_address(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await _reconfigure(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new = {"host": "192.168.79.99", "community": "other", "port": 1161}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], new)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert dict(entry.data) == new
    assert entry.state is ConfigEntryState.LOADED


async def test_reconfigure_refuses_another_switch(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    other = {**SYSTEM, OID_SYS_NAME: b"OTHER", OID_BRIDGE_ADDRESS: bytes.fromhex("aabbccddeeff")}
    snmp.get.side_effect = lambda *oids: {o: other[o] for o in oids if o in other}

    result = await _reconfigure(hass, entry)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert entry.data["host"] == "192.168.79.15"  # unchanged


async def test_reconfigure_with_a_silent_switch(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    snmp.get.side_effect = SnmpError("timeout")

    result = await _reconfigure(hass, entry)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data["host"] == "192.168.79.15"
