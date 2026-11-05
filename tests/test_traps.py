"""Tests for the trap receiver: real UDP on the loopback address, and its use by the setup."""

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    NotificationType,
    ObjectIdentity,
    SnmpEngine,
    UdpTransportTarget,
    send_notification,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.tplink_switch_snmp import traps
from custom_components.tplink_switch_snmp.const import EVENT_ALARM

LINK_DOWN = "1.3.6.1.6.3.1.1.5.3"
CPU_LOAD = "1.3.6.1.4.1.11863.1.1.3.14.12.1"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _send(port: int, community: str, trap: str = LINK_DOWN) -> None:
    # A new engine per trap: one engine keeps using the first community it was given.
    engine = SnmpEngine()
    target = await UdpTransportTarget.create(("127.0.0.1", port))
    await send_notification(
        engine,
        CommunityData(community, mpModel=1),
        target,
        ContextData(),
        "trap",
        NotificationType(ObjectIdentity(trap)),
    )
    await asyncio.sleep(0.3)
    engine.close_dispatcher()


@pytest.fixture
async def receiver(socket_enabled):
    port = _free_port()
    receiver = traps.TrapReceiver(port, "127.0.0.1")
    await receiver.start()
    yield receiver
    await receiver.stop()


async def test_a_trap_from_a_known_switch_calls_the_handler(receiver) -> None:
    handler = MagicMock()
    receiver.add("127.0.0.1", "homeassistant", handler)

    await _send(receiver.port, "homeassistant")

    handler.assert_called_once_with(LINK_DOWN)


async def test_a_trap_with_the_wrong_community_is_dropped(receiver) -> None:
    handler = MagicMock()
    receiver.add("127.0.0.1", "homeassistant", handler)

    await _send(receiver.port, "wrong")

    handler.assert_not_called()


async def test_a_trap_from_another_address_is_dropped(receiver) -> None:
    handler = MagicMock()
    receiver.add("192.168.79.15", "homeassistant", handler)  # the trap comes from 127.0.0.1

    await _send(receiver.port, "homeassistant")

    handler.assert_not_called()


async def test_a_removed_handler_is_not_called(receiver) -> None:
    handler = MagicMock()
    remove = receiver.add("127.0.0.1", "homeassistant", handler)
    assert not receiver.idle
    remove()
    assert receiver.idle

    await _send(receiver.port, "homeassistant")

    handler.assert_not_called()


async def test_two_switches_share_one_port(receiver) -> None:
    mine, other = MagicMock(), MagicMock()
    receiver.add("127.0.0.1", "homeassistant", mine)
    receiver.add("192.168.79.99", "other", other)

    await _send(receiver.port, "homeassistant")

    mine.assert_called_once_with(LINK_DOWN)
    other.assert_not_called()


async def test_a_port_that_is_taken_raises(socket_enabled) -> None:
    port = _free_port()
    first = traps.TrapReceiver(port, "127.0.0.1")
    await first.start()
    try:
        with pytest.raises(OSError):
            await traps.TrapReceiver(port, "127.0.0.1").start()
    finally:
        await first.stop()


async def test_subscribers_share_a_receiver_and_the_last_one_closes_it(
    hass: HomeAssistant, socket_enabled
) -> None:
    port = _free_port()
    original = traps.TrapReceiver
    with patch.object(traps, "TrapReceiver", lambda p: original(p, "127.0.0.1")):
        first = await traps.async_subscribe(hass, port, "127.0.0.1", "a", MagicMock())
        second = await traps.async_subscribe(hass, port, "127.0.0.2", "b", MagicMock())
        receivers = hass.data["tplink_switch_snmp"][traps.DATA_RECEIVERS]
        assert list(receivers) == [port]

        await first()
        assert port in receivers  # the second one still listens
        await second()
        assert receivers == {}  # closed


# ---- the setup -----------------------------------------------------------------------------


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, **update) -> None:
    entry.add_to_hass(hass)
    if update:
        hass.config_entries.async_update_entry(entry, **update)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_traps_are_off_by_default(hass: HomeAssistant, snmp, entry) -> None:
    with patch("custom_components.tplink_switch_snmp.async_subscribe", AsyncMock()) as subscribe:
        await _setup(hass, entry)
    subscribe.assert_not_called()


def _polls(snmp) -> int:
    """How often the interface tables were read (TP-Link's own tables come on top)."""
    return sum("name" in call.args[0] for call in snmp.walk_many.await_args_list)


async def test_a_trap_triggers_a_poll(hass: HomeAssistant, snmp, entry) -> None:
    unsubscribe = AsyncMock()
    with patch(
        "custom_components.tplink_switch_snmp.async_subscribe",
        AsyncMock(return_value=unsubscribe),
    ) as subscribe:
        await _setup(hass, entry, options={"trap_port": 1162})

    args = subscribe.await_args.args
    assert args[1:4] == (1162, "192.168.79.15", "homeassistant")
    polls = _polls(snmp)

    args[4](LINK_DOWN)  # the handler the setup passed: a trap arrives
    await hass.async_block_till_done()

    assert _polls(snmp) == polls + 1


async def test_unload_closes_the_listener(hass: HomeAssistant, snmp, entry) -> None:
    unsubscribe = AsyncMock()
    with patch(
        "custom_components.tplink_switch_snmp.async_subscribe",
        AsyncMock(return_value=unsubscribe),
    ):
        await _setup(hass, entry, options={"trap_port": 1162})
    assert await hass.config_entries.async_unload(entry.entry_id)

    unsubscribe.assert_awaited_once()


async def test_a_port_that_cannot_be_opened_does_not_stop_the_setup(
    hass: HomeAssistant, snmp, entry, caplog
) -> None:
    with patch(
        "custom_components.tplink_switch_snmp.async_subscribe",
        AsyncMock(side_effect=OSError("address already in use")),
    ):
        await _setup(hass, entry, options={"trap_port": 1162})

    assert entry.state is ConfigEntryState.LOADED
    assert "Cannot receive traps on UDP port 1162" in caplog.text


async def test_v3_does_not_receive_traps(hass: HomeAssistant, snmp, entry, caplog) -> None:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry,
        data={
            "host": "192.168.79.15",
            "port": 161,
            "version": "3",
            "username": "ha",
            "auth_protocol": "none",
            "priv_protocol": "none",
        },
        options={"trap_port": 1162},
    )
    with patch("custom_components.tplink_switch_snmp.async_subscribe", AsyncMock()) as subscribe:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    subscribe.assert_not_called()
    assert "only supported with SNMP v1 and v2c" in caplog.text


async def test_changing_the_trap_port_reloads(hass: HomeAssistant, snmp, entry) -> None:
    with patch(
        "custom_components.tplink_switch_snmp.async_subscribe",
        AsyncMock(return_value=AsyncMock()),
    ) as subscribe:
        await _setup(hass, entry, options={"trap_port": 1162})
        assert subscribe.await_count == 1

        hass.config_entries.async_update_entry(entry, options={"trap_port": 2162})
        await hass.async_block_till_done()

        assert subscribe.await_count == 2
        assert subscribe.await_args.args[1] == 2162


async def test_other_option_changes_do_not_reload(hass: HomeAssistant, snmp, entry) -> None:
    with patch(
        "custom_components.tplink_switch_snmp.async_subscribe",
        AsyncMock(return_value=AsyncMock()),
    ) as subscribe:
        await _setup(hass, entry, options={"trap_port": 1162})

        hass.config_entries.async_update_entry(
            entry, options={"trap_port": 1162, "port_names": {"1": "NAS"}}
        )
        await hass.async_block_till_done()

        assert subscribe.await_count == 1


async def test_the_handler_gets_the_oid_of_the_trap(receiver) -> None:
    handler = MagicMock()
    receiver.add("127.0.0.1", "homeassistant", handler)

    await _send(receiver.port, "homeassistant", CPU_LOAD)

    handler.assert_called_once_with(CPU_LOAD)


async def test_an_alarm_trap_fires_an_event(hass: HomeAssistant, snmp, entry) -> None:
    with patch(
        "custom_components.tplink_switch_snmp.async_subscribe",
        AsyncMock(return_value=AsyncMock()),
    ) as subscribe:
        await _setup(hass, entry, options={"trap_port": 1162})
    events = async_capture_events(hass, EVENT_ALARM)
    on_trap = subscribe.await_args.args[4]

    on_trap(CPU_LOAD)
    on_trap(LINK_DOWN)  # a trap that is no alarm
    on_trap(None)  # a trap without an OID
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data == {
        "entry_id": entry.entry_id,
        "switch": "TL-SG3424",
        "alarm": "cpu_load",
    }
