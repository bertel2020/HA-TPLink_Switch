"""Tests for writing to the switch: ports on and off, and names at the switch."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pysnmp.proto.rfc1902 import Integer32
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp import model, snmp as module
from custom_components.tplink_switch_snmp.const import (
    DOMAIN,
    OID_IF_ADMIN_STATUS,
    OID_IF_ALIAS,
)
from custom_components.tplink_switch_snmp.diagnostics import async_get_config_entry_diagnostics
from custom_components.tplink_switch_snmp.snmp import SnmpClient, SnmpError

from .conftest import BRIDGE_MAC

WRITE = {"allow_write": True, "write_community": "private"}


def _client(config: dict) -> SnmpClient:
    client = SnmpClient(MagicMock(), "192.168.79.15", 161, config)
    client._target = MagicMock()  # skip the real transport
    return client


# ---- the client --------------------------------------------------------------------------


def test_v2c_writes_with_its_own_community() -> None:
    config = {"version": "2c", "community": "public", "write_community": "private"}

    assert _name(module.build_auth(config)) == "public"
    assert _name(module.build_auth(config, write=True)) == "private"


def _name(auth) -> str:
    return getattr(auth, "community_name", None) or auth.communityName


def test_v2c_without_a_write_community_cannot_write() -> None:
    for config in (
        {"version": "2c", "community": "public"},
        {"version": "1", "community": "p", "write_community": ""},
    ):
        with pytest.raises(SnmpError, match="no write community"):
            module.build_auth(config, write=True)


def test_v3_writes_with_the_same_user() -> None:
    config = {"version": "3", "username": "ha", "auth_protocol": "none", "priv_protocol": "none"}

    assert module.build_auth(config, write=True).userName == "ha"


async def test_set_sends_the_value() -> None:
    client = _client({"version": "2c", "community": "public", "write_community": "private"})
    with (
        patch.object(module, "set_cmd", AsyncMock(return_value=(None, 0, 0, []))) as set_cmd,
        patch.object(module, "ObjectType") as object_type,
    ):
        await client.set("1.3.6.1.2.1.2.2.1.7.3", 2)

    set_cmd.assert_awaited_once()
    assert _name(set_cmd.await_args.args[1]) == "private"  # the write community, not the read one
    value = object_type.call_args.args[1]
    assert isinstance(value, Integer32) and int(value) == 2


async def test_set_text_is_sent_as_text() -> None:
    client = _client({"version": "2c", "community": "public", "write_community": "private"})
    with (
        patch.object(module, "set_cmd", AsyncMock(return_value=(None, 0, 0, []))),
        patch.object(module, "ObjectType") as object_type,
    ):
        await client.set("1.3.6.1.2.1.31.1.1.1.18.3", "NAS")

    assert bytes(object_type.call_args.args[1]) == b"NAS"


async def test_a_switch_that_says_nothing_to_a_write_is_explained() -> None:
    client = _client({"version": "2c", "community": "public", "write_community": "private"})
    with (
        patch.object(
            module, "set_cmd", AsyncMock(return_value=("No SNMP response received", 0, 0, []))
        ),
        pytest.raises(SnmpError, match="read-only community"),
    ):
        await client.set("1.3.6.1.2.1.2.2.1.7.3", 2)


async def test_an_error_status_is_reported() -> None:
    status = MagicMock()
    status.prettyPrint.return_value = "notWritable"
    client = _client({"version": "2c", "community": "public", "write_community": "private"})
    with (
        patch.object(module, "set_cmd", AsyncMock(return_value=(None, status, 1, []))),
        pytest.raises(SnmpError, match="notWritable"),
    ):
        await client.set("1.3.6.1.2.1.2.2.1.7.3", 2)


# ---- the model ---------------------------------------------------------------------------


def _tables(**extra):
    base = {
        "name": {"1": b"port 1: x"},
        "oper": {"1": 1},
        "speed": {"1": 1000},
        "rx": {"1": 0},
        "tx": {"1": 0},
        "rx_err": {"1": 0},
        "tx_err": {"1": 0},
    }
    return {**base, **extra}


def test_admin_state_and_alias_are_read() -> None:
    port = model.build_ports(_tables(admin={"1": 2}, alias={"1": b" NAS "}), {}, {})[1]

    assert port.admin_up is False
    assert port.alias == "NAS"


def test_a_switch_without_those_columns_is_taken_as_on_and_unnamed() -> None:
    port = model.build_ports(_tables(), {}, {})[1]

    assert port.admin_up is True and port.alias == ""


# ---- the entities ------------------------------------------------------------------------


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, **options) -> None:
    entry.add_to_hass(hass)
    if options:
        hass.config_entries.async_update_entry(entry, options=options)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _switch(hass: HomeAssistant, port: int) -> str | None:
    return er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{BRIDGE_MAC}_port{port}_enabled"
    )


async def _call(hass: HomeAssistant, service: str, port: int) -> None:
    await hass.services.async_call(
        "switch", service, {"entity_id": _switch(hass, port)}, blocking=True
    )


async def test_without_the_option_there_are_no_switches(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)

    assert _switch(hass, 1) is None
    assert not entry.runtime_data.can_write


async def test_with_the_option_every_port_gets_a_switch(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry, **WRITE)

    assert hass.states.get(_switch(hass, 1)).state == "on"
    assert hass.states.get(_switch(hass, 2)).state == "on"
    assert hass.states.get(_switch(hass, 2)).attributes["port"] == 2


async def test_a_port_that_is_switched_off_shows_as_off(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["admin"]["2"] = 2
    await _setup(hass, entry, **WRITE)

    assert hass.states.get(_switch(hass, 2)).state == "off"


async def test_turning_a_port_off_and_on_writes_the_admin_status(
    hass: HomeAssistant, snmp, entry
) -> None:
    await _setup(hass, entry, **WRITE)

    await _call(hass, "turn_off", 2)
    snmp.set.assert_awaited_with(f"{OID_IF_ADMIN_STATUS}.2", 2)
    await _call(hass, "turn_on", 2)
    snmp.set.assert_awaited_with(f"{OID_IF_ADMIN_STATUS}.2", 1)


async def test_the_state_follows_after_the_write(hass: HomeAssistant, snmp, entry, tables) -> None:
    await _setup(hass, entry, **WRITE)
    polls = snmp.walk_many.await_count

    tables["admin"]["2"] = 2  # what the switch reports after the write
    await _call(hass, "turn_off", 2)
    await hass.async_block_till_done()

    assert snmp.walk_many.await_count > polls
    assert hass.states.get(_switch(hass, 2)).state == "off"


async def test_a_port_chosen_in_the_options_is_never_switched_off(
    hass: HomeAssistant, snmp, entry
) -> None:
    await _setup(hass, entry, **WRITE, protected_ports=[2])

    with pytest.raises(ServiceValidationError, match="protected"):
        await _call(hass, "turn_off", 2)
    snmp.set.assert_not_awaited()
    await _call(hass, "turn_off", 1)  # the other one is not protected
    snmp.set.assert_awaited_once_with(f"{OID_IF_ADMIN_STATUS}.1", 2)


async def test_switching_a_protected_port_on_is_allowed(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["admin"]["2"] = 2
    await _setup(hass, entry, **WRITE, protected_ports=[2])

    await _call(hass, "turn_on", 2)

    snmp.set.assert_awaited_once_with(f"{OID_IF_ADMIN_STATUS}.2", 1)


async def test_an_uplink_with_many_devices_is_protected(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    for n in range(10):
        tables["fdb_q"][f"1.0.1.2.3.4.{n}"] = 2  # ten MAC addresses learned at port 2
    await _setup(hass, entry, **WRITE)

    assert entry.runtime_data.is_protected(2)
    with pytest.raises(ServiceValidationError, match="protected"):
        await _call(hass, "turn_off", 2)
    snmp.set.assert_not_awaited()


async def test_a_failed_write_is_reported_to_the_user(hass: HomeAssistant, snmp, entry) -> None:
    snmp.set.side_effect = SnmpError(
        "No SNMP response received (a read-only community gets no answer)"
    )
    await _setup(hass, entry, **WRITE)

    with pytest.raises(HomeAssistantError, match="could not be changed"):
        await _call(hass, "turn_off", 1)


async def test_the_write_community_reaches_the_client(hass: HomeAssistant, snmp, entry) -> None:
    with patch("custom_components.tplink_switch_snmp.SnmpClient", return_value=snmp) as client:
        await _setup(hass, entry, **WRITE)

    assert client.call_args.args[3]["write_community"] == "private"


async def test_switching_writing_on_in_the_options_adds_the_switches(
    hass: HomeAssistant, snmp, entry
) -> None:
    await _setup(hass, entry)
    assert _switch(hass, 1) is None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"scan_interval": 30, "trap_port": 0, "allow_write": True, "write_community": "private"},
    )
    await hass.async_block_till_done()

    assert _switch(hass, 1) is not None


async def test_the_options_offer_the_ports_to_protect(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    done = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"scan_interval": 30, "trap_port": 0, "allow_write": False, "protected_ports": ["1", "2"]},
    )

    assert done["data"]["protected_ports"] == [1, 2]
    assert [k.schema for k in result["data_schema"].schema if str(k) == "protected_ports"]


async def test_an_unknown_port_is_refused(hass: HomeAssistant, snmp, entry) -> None:
    await _setup(hass, entry, **WRITE)

    with pytest.raises(ServiceValidationError, match="no port 99"):
        await entry.runtime_data.async_set_port_enabled(99, True)


# ---- names at the switch -----------------------------------------------------------------


async def _ws(hass, hass_ws_client, payload):
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(payload)
    return await client.receive_json()


async def test_the_switch_name_is_the_default_and_a_name_of_your_own_wins(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "tplink_switch_snmp/snapshot"})
    port = (await client.receive_json())["result"]["switches"][0]["ports"][0]
    assert (port["name"], port["alias"], port["custom_name"]) == (
        "Lenovo M920q-1",
        "Lenovo M920q-1",
        "",
    )
    assert port["admin_up"] is True

    await client.send_json_auto_id(
        {
            "type": "tplink_switch_snmp/set_port_name",
            "entry_id": entry.entry_id,
            "port": 1,
            "name": "NAS",
        }
    )
    await client.receive_json()
    await client.send_json_auto_id({"type": "tplink_switch_snmp/snapshot"})
    port = (await client.receive_json())["result"]["switches"][0]["ports"][0]
    assert (port["name"], port["alias"], port["custom_name"]) == ("NAS", "Lenovo M920q-1", "NAS")


async def test_a_name_can_be_saved_at_the_switch_too(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry, **WRITE)

    msg = await _ws(
        hass,
        hass_ws_client,
        {
            "type": "tplink_switch_snmp/set_port_name",
            "entry_id": entry.entry_id,
            "port": 1,
            "name": "NAS",
            "to_switch": True,
        },
    )

    assert msg["success"] is True
    snmp.set.assert_awaited_once_with(f"{OID_IF_ALIAS}.1", "NAS")


async def test_saving_at_the_switch_needs_writing_to_be_on(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry)

    msg = await _ws(
        hass,
        hass_ws_client,
        {
            "type": "tplink_switch_snmp/set_port_name",
            "entry_id": entry.entry_id,
            "port": 1,
            "name": "NAS",
            "to_switch": True,
        },
    )

    assert msg["success"] is False and msg["error"]["code"] == "write_failed"
    snmp.set.assert_not_awaited()


async def test_the_snapshot_says_whether_writing_is_on(
    hass: HomeAssistant, hass_ws_client, snmp, entry
) -> None:
    await _setup(hass, entry, **WRITE)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "tplink_switch_snmp/snapshot"})

    assert (await client.receive_json())["result"]["switches"][0]["can_write"] is True


async def test_events_and_device_sensors_use_the_name_at_the_switch(
    hass: HomeAssistant, snmp, entry
) -> None:
    await _setup(hass, entry)

    assert entry.runtime_data.port_label(1) == "Lenovo M920q-1"
    assert entry.runtime_data.port_label(2) == ""
    assert entry.runtime_data.port_label(99) == ""


async def test_the_write_community_is_not_in_the_diagnostics(
    hass: HomeAssistant, snmp, entry
) -> None:
    await _setup(hass, entry, **WRITE)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert "private" not in str(diagnostics)
    assert diagnostics["entry"]["options"]["write_community"] == "**REDACTED**"
