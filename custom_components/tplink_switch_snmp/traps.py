"""Receive SNMP traps, so a link change shows up at once instead of at the next poll."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
import logging
import socket
from typing import Any

from homeassistant.core import HomeAssistant
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.hlapi.v3arch.asyncio import SnmpEngine

_LOGGER = logging.getLogger(__name__)

OID_SNMP_TRAP = "1.3.6.1.6.3.1.1.4.1.0"  # snmpTrapOID.0: which trap this is

# called with the OID of the trap, which is None if the trap does not carry one
type TrapHandler = Callable[[str | None], None]


class TrapReceiver:
    """One UDP port that receives v1 and v2c traps from several switches.

    A trap is accepted if its community and its sender address are both registered for
    a handler; that handler is then called with the kind of trap. What changed is read by
    the poll that follows.
    """

    def __init__(self, port: int, bind: str = "0.0.0.0") -> None:
        self.port = port
        self._bind = bind
        self._engine: SnmpEngine | None = None
        self._handlers: dict[tuple[str, str], TrapHandler] = {}  # (address, community)
        self._communities: dict[str, str] = {}  # community -> its index in the engine

    async def start(self) -> None:
        """Open the port; raises OSError if it cannot be used."""
        # Bind the socket here: pysnmp binds a port in the background, so a port that is
        # taken or not allowed would only show up later, and not as an error to the caller.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self._bind, self.port))
            sock.setblocking(False)
        except OSError:
            sock.close()
            raise
        # Creating the engine loads MIB data from disk, so keep it off the event loop.
        engine = await asyncio.get_running_loop().run_in_executor(None, SnmpEngine)
        try:
            config.add_transport(
                engine, udp.DOMAIN_NAME, udp.UdpTransport().open_server_mode(sock=sock)
            )
            ntfrcv.NotificationReceiver(engine, self._on_notification)
        except Exception:
            engine.close_dispatcher()
            sock.close()
            raise
        self._engine = engine

    async def stop(self) -> None:
        """Close the port."""
        if self._engine is not None:
            self._engine.close_dispatcher()
            self._engine = None

    @property
    def idle(self) -> bool:
        """Whether nobody listens through this receiver any more."""
        return not self._handlers

    def add(self, address: str, community: str, handler: TrapHandler) -> Callable[[], None]:
        """Call the handler for traps from this address with this community."""
        assert self._engine is not None
        if community not in self._communities:
            index = f"c{len(self._communities)}"
            config.add_v1_system(self._engine, index, community)
            self._communities[community] = index
        key = (address, community)
        self._handlers[key] = handler

        def remove() -> None:
            self._handlers.pop(key, None)

        return remove

    def _on_notification(
        self,
        engine: SnmpEngine,
        state_reference: Any,
        context_engine_id: Any,
        context_name: Any,
        var_binds: Any,
        _ctx: Any,
    ) -> None:
        _domain, source = engine.message_dispatcher.get_transport_info(state_reference)
        address = str(source[0])
        # pysnmp has already dropped traps with an unknown community; find which one this was.
        trap = next((str(value) for name, value in var_binds if str(name) == OID_SNMP_TRAP), None)
        for (known, _community), handler in list(self._handlers.items()):
            if known == address:
                _LOGGER.debug("Trap %s from %s", trap, address)
                handler(trap)
                return
        _LOGGER.debug("Trap from %s ignored: no switch with that address", address)


DATA_RECEIVERS = "trap_receivers"
DATA_LOCK = "trap_lock"


async def async_subscribe(
    hass: HomeAssistant, port: int, address: str, community: str, handler: TrapHandler
) -> Callable[[], Coroutine[Any, Any, None]]:
    """Call the handler for traps from this address; switches on one port share a receiver.

    Raises OSError if the port cannot be opened. Returns the function that ends the
    subscription and closes the port once nobody uses it any more.
    """
    domain_data = hass.data.setdefault("tplink_switch_snmp", {})
    lock = domain_data.setdefault(DATA_LOCK, asyncio.Lock())
    receivers: dict[int, TrapReceiver] = domain_data.setdefault(DATA_RECEIVERS, {})

    async with lock:
        receiver = receivers.get(port)
        if receiver is None:
            receiver = TrapReceiver(port)
            await receiver.start()
            receivers[port] = receiver
        remove = receiver.add(address, community, handler)

    async def unsubscribe() -> None:
        async with lock:
            remove()
            if receiver.idle and receivers.get(port) is receiver:
                del receivers[port]
                await receiver.stop()

    return unsubscribe
