"""Edge cases: what happens with odd answers, failures on the way and repeated set-ups."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pysnmp.proto.rfc1902 import ObjectIdentifier
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp import model, panel, snmp as module, traps
from custom_components.tplink_switch_snmp.config_flow import check_user
from custom_components.tplink_switch_snmp.const import PANEL_PATH
from custom_components.tplink_switch_snmp.snmp import SnmpClient, SnmpError

# ---- the set-up dialog -------------------------------------------------------------------


def test_a_short_encryption_key_is_refused() -> None:
    data = {
        "auth_protocol": "sha",
        "auth_key": "authpassword",
        "priv_protocol": "aes128",
        "priv_key": "short",
    }

    assert check_user(data) == "key_too_short"
    assert check_user({**data, "priv_key": "privpassword"}) is None


async def test_saved_protected_ports_are_shown_as_text(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"protected_ports": [1, 24]})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    shown = {str(key): key.description for key in result["data_schema"].schema}
    assert shown["protected_ports"]["suggested_value"] == ["1", "24"]


# ---- the poll ----------------------------------------------------------------------------


async def test_a_switch_that_lists_no_ports_is_not_set_up(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    tables["name"], tables["oper"], tables["base_port"] = {}, {}, {}
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


# ---- the data model ----------------------------------------------------------------------


def test_a_mac_may_already_be_text() -> None:
    assert model.format_mac("AA:BB:CC:DD:EE:FF") == "aa:bb:cc:dd:ee:ff"


def test_odd_forwarding_table_indexes_are_skipped() -> None:
    assert model.mac_from_suffix("1.2.3") is None
    assert model.mac_from_suffix("1.x.3.4.5.6.7") is None
    assert model.mac_from_suffix("1.0.4.32.249.54.2") == "00:04:20:f9:36:02"


def test_a_forwarding_entry_that_cannot_be_read_is_ignored() -> None:
    tables = {
        "name": {"1": b"port 1"},
        "oper": {"1": 1},
        "speed": {"1": 1000},
        "rx": {},
        "tx": {},
        "rx_err": {},
        "tx_err": {},
    }
    fdb = {"1.0.x": 1, "1.0.4.32.249.54.2": "not a port number"}

    assert model.build_ports(tables, fdb, {"1": 1})[1].macs == []


def test_a_port_that_was_not_there_before_has_no_rate() -> None:
    port = model.PortData(1, 1, "p", True, 1000, 100, 100, 0, 0)
    model.add_rates({1: port}, {2: port}, 1.0)

    assert port.rx_rate is None


# ---- the SNMP client ---------------------------------------------------------------------


def _client() -> SnmpClient:
    return SnmpClient(MagicMock(), "192.168.79.15", 161, {"version": "2c", "community": "c"})


def test_an_object_identifier_comes_back_as_text() -> None:
    assert module._py(ObjectIdentifier("1.3.6.1.4.1.11863.1.1.3")) == "1.3.6.1.4.1.11863.1.1.3"


def test_close_releases_the_engine() -> None:
    client = _client()

    client.close()

    client._engine.close_dispatcher.assert_called_once_with()


async def test_the_target_is_created_once() -> None:
    client = _client()
    target = MagicMock()
    with patch.object(
        module.UdpTransportTarget, "create", AsyncMock(return_value=target)
    ) as create:
        assert await client._get_target() is target
        assert await client._get_target() is target

    create.assert_awaited_once()


async def test_an_address_that_cannot_be_used_is_an_snmp_error() -> None:
    with (
        patch.object(
            module.UdpTransportTarget, "create", AsyncMock(side_effect=OSError("no route"))
        ),
        pytest.raises(SnmpError, match="cannot reach 192.168.79.15"),
    ):
        await _client()._get_target()


async def test_a_walk_that_the_switch_refuses_is_reported() -> None:
    status = MagicMock()
    status.prettyPrint.return_value = "noAccess"

    async def walk(*_args, **_kwargs):
        yield (None, status, 1, [])

    client = _client()
    client._target = MagicMock()
    with (
        patch.object(module, "bulk_walk_cmd", walk),
        pytest.raises(SnmpError, match="noAccess"),
    ):
        await client.walk("1.3.6.1.2.1.2.2.1.8")


# ---- traps -------------------------------------------------------------------------------


async def test_a_receiver_that_fails_to_start_closes_what_it_opened(socket_enabled) -> None:
    receiver = traps.TrapReceiver(0, "127.0.0.1")
    engine = MagicMock()
    with (
        patch.object(traps, "SnmpEngine", return_value=engine),
        patch.object(traps.config, "add_transport", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await receiver.start()

    engine.close_dispatcher.assert_called_once_with()


# ---- the panel ---------------------------------------------------------------------------


async def test_a_panel_that_is_already_there_is_not_registered_again(hass: HomeAssistant) -> None:
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.config.components.add("frontend")
    hass.data[frontend.DATA_PANELS] = {PANEL_PATH: object()}
    with (
        patch.object(panel.frontend, "add_extra_js_url"),
        patch.object(panel.panel_custom, "async_register_panel", AsyncMock()) as register,
    ):
        await panel.async_register_panel(hass)

    register.assert_not_awaited()


def test_the_panel_is_taken_out_when_the_last_switch_goes(hass: HomeAssistant) -> None:
    hass.data[frontend.DATA_PANELS] = {PANEL_PATH: object()}
    with patch.object(panel.frontend, "async_remove_panel") as remove:
        panel.async_remove_panel(hass)

    remove.assert_called_once_with(hass, PANEL_PATH)


def test_nothing_is_removed_if_the_panel_is_not_there(hass: HomeAssistant) -> None:
    hass.data[frontend.DATA_PANELS] = {}
    with patch.object(panel.frontend, "async_remove_panel") as remove:
        panel.async_remove_panel(hass)

    remove.assert_not_called()


async def test_the_panel_goes_with_the_last_switch(hass: HomeAssistant, snmp, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    second = MockConfigEntry(
        domain=entry.domain, unique_id="aa:bb:cc:dd:ee:ff", data=entry.data, title="Second"
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    with patch("custom_components.tplink_switch_snmp.async_remove_panel") as remove:
        assert await hass.config_entries.async_unload(entry.entry_id)
        remove.assert_not_called()  # one switch is still there
        assert await hass.config_entries.async_unload(second.entry_id)
        remove.assert_called_once_with(hass)
