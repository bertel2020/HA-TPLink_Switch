"""Tests for the buttons that save the configuration and restart the switch."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.tplink_switch_snmp.const import DOMAIN, OID_REBOOT, OID_SAVE_CONFIG
from custom_components.tplink_switch_snmp.snmp import SnmpError

from .conftest import BRIDGE_MAC

WRITE = {"allow_write": True, "write_community": "private"}


async def _setup(hass: HomeAssistant, entry, **options) -> None:
    entry.add_to_hass(hass)
    if options:
        hass.config_entries.async_update_entry(entry, options=options)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _button(hass: HomeAssistant, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{BRIDGE_MAC}_{key}")


async def test_no_buttons_unless_writing_is_allowed(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)
    assert _button(hass, "save_config") is None
    assert _button(hass, "reboot") is None


async def test_the_save_button_writes_the_save_object(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry, **WRITE)
    button = _button(hass, "save_config")
    assert button

    await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)

    snmp.set.assert_awaited_once_with(OID_SAVE_CONFIG, 1)


async def test_the_restart_button_is_off_until_it_is_wanted(
    hass: HomeAssistant, snmp, entry
) -> None:
    from custom_components.tplink_switch_snmp.button import Reboot

    await _setup(hass, entry, **WRITE)
    reboot = _button(hass, "reboot")
    assert reboot
    assert er.async_get(hass).async_get(reboot).disabled

    await Reboot(entry.runtime_data).async_press()  # disabled, so press it directly
    snmp.set.assert_awaited_once_with(OID_REBOOT, 1)


async def test_a_switch_that_refuses_the_action(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry, **WRITE)
    snmp.set.side_effect = SnmpError("notWritable")

    with pytest.raises(HomeAssistantError, match="notWritable"):
        await entry.runtime_data.async_save_config()


async def test_the_actions_need_writing_to_be_allowed(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await entry.runtime_data.async_reboot()
    snmp.set.assert_not_awaited()
