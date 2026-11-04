"""Tests for the config flow."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tplink_switch_snmp.const import DOMAIN, OID_BRIDGE_ADDRESS, OID_SYS_NAME
from custom_components.tplink_switch_snmp.snmp import SnmpError

from .conftest import BRIDGE_MAC, SYSTEM

ADDRESS = {"host": "192.168.79.15", "port": 161, "version": "2c"}
COMMUNITY = {"community": "homeassistant"}
USER_V3 = {
    "username": "ha",
    "auth_protocol": "sha",
    "auth_key": "authpassword",
    "priv_protocol": "aes128",
    "priv_key": "privpassword",
}


async def _start(hass: HomeAssistant, address: dict | None = None) -> dict:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(result["flow_id"], address or ADDRESS)


async def test_v2c_flow_creates_entry(hass: HomeAssistant, snmp) -> None:
    result = await _start(hass)
    assert result["step_id"] == "community"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "TL-SG3424"
    assert result["data"] == {**ADDRESS, **COMMUNITY}
    assert result["result"].unique_id == BRIDGE_MAC


async def test_v1_asks_for_a_community_too(hass: HomeAssistant, snmp) -> None:
    result = await _start(hass, {**ADDRESS, "version": "1"})
    assert result["step_id"] == "community"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["version"] == "1"


async def test_v3_flow_asks_for_a_user(hass: HomeAssistant, snmp) -> None:
    result = await _start(hass, {**ADDRESS, "version": "3"})
    assert result["step_id"] == "auth"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_V3)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {**ADDRESS, "version": "3", **USER_V3}


async def test_v3_without_authentication(hass: HomeAssistant, snmp) -> None:
    result = await _start(hass, {**ADDRESS, "version": "3"})
    user = {"username": "ha", "auth_protocol": "none", "priv_protocol": "none"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user)

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_v3_short_key_is_refused(hass: HomeAssistant, snmp) -> None:
    result = await _start(hass, {**ADDRESS, "version": "3"})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_V3, "auth_key": "short"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "key_too_short"}


async def test_v3_encryption_needs_authentication(hass: HomeAssistant, snmp) -> None:
    result = await _start(hass, {**ADDRESS, "version": "3"})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_V3, "auth_protocol": "none", "auth_key": ""}
    )

    assert result["errors"] == {"base": "privacy_needs_authentication"}


async def test_switch_that_does_not_answer(hass: HomeAssistant, snmp) -> None:
    snmp.get.side_effect = SnmpError("timeout")
    result = await _start(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_device_without_bridge_address_is_refused(hass: HomeAssistant, snmp) -> None:
    snmp.get.side_effect = lambda *oids: {}
    result = await _start(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)

    assert result["errors"] == {"base": "cannot_connect"}


async def test_error_can_be_corrected(hass: HomeAssistant, snmp) -> None:
    good = snmp.get.side_effect
    snmp.get.side_effect = SnmpError("timeout")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)
    assert result["errors"]

    snmp.get.side_effect = good
    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_same_switch_twice_updates_the_address(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    result = await _start(hass, {**ADDRESS, "host": "192.168.79.99"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == "192.168.79.99"


async def test_reconfigure_changes_the_address(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    new = {"host": "192.168.79.99", "port": 1161, "version": "2c"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], new)
    assert result["step_id"] == "community"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"community": "other"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert dict(entry.data) == {**new, "community": "other"}
    assert entry.state is ConfigEntryState.LOADED


async def test_reconfigure_to_v3_drops_the_community(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**ADDRESS, "version": "3"}
    )
    assert result["step_id"] == "auth"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_V3)
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    assert "community" not in entry.data
    assert entry.data["username"] == "ha"


async def test_reconfigure_refuses_another_switch(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    other = {**SYSTEM, OID_SYS_NAME: b"OTHER", OID_BRIDGE_ADDRESS: bytes.fromhex("aabbccddeeff")}
    snmp.get.side_effect = lambda *oids: {o: other[o] for o in oids if o in other}

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ADDRESS)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert entry.data["host"] == "192.168.79.15"  # unchanged


async def test_reconfigure_with_a_silent_switch(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    snmp.get.side_effect = SnmpError("timeout")

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ADDRESS)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], COMMUNITY)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data["host"] == "192.168.79.15"
