"""Data update coordinator for the switch."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PORT_NAMES,
    CONF_SCAN_INTERVAL,
    CONF_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERSION,
    DOMAIN,
    EVENT_LINK_CHANGED,
    OID_BASE_PORT_IF_INDEX,
    OID_FDB,
    OID_FDB_Q,
    OID_IF_HC_IN_OCTETS,
    OID_IF_HC_OUT_OCTETS,
    OID_IF_HIGH_SPEED,
    OID_IF_IN_DISCARDS,
    OID_IF_IN_ERRORS,
    OID_IF_IN_OCTETS,
    OID_IF_LAST_CHANGE,
    OID_IF_NAME,
    OID_IF_OPER_STATUS,
    OID_IF_OUT_DISCARDS,
    OID_IF_OUT_ERRORS,
    OID_IF_OUT_OCTETS,
    OID_SYS_DESCR,
    OID_SYS_OBJECT_ID,
    OID_SYS_UPTIME,
    VERSION_1,
)
from .model import PortData, SwitchData, UptimeTracker, add_rates, build_ports, text
from .snmp import SnmpClient, SnmpError

_LOGGER = logging.getLogger(__name__)

TABLES = {
    "name": OID_IF_NAME,
    "oper": OID_IF_OPER_STATUS,
    "speed": OID_IF_HIGH_SPEED,
    "rx": OID_IF_HC_IN_OCTETS,
    "tx": OID_IF_HC_OUT_OCTETS,
    "rx_err": OID_IF_IN_ERRORS,
    "tx_err": OID_IF_OUT_ERRORS,
    "last_change": OID_IF_LAST_CHANGE,
    "rx_disc": OID_IF_IN_DISCARDS,
    "tx_disc": OID_IF_OUT_DISCARDS,
    "fdb_q": OID_FDB_Q,
    "fdb": OID_FDB,
    "base_port": OID_BASE_PORT_IF_INDEX,
}

# SNMPv1 has no 64 bit counters: it reads the 32 bit ones, which wrap quickly.
TABLES_V1 = {**TABLES, "rx": OID_IF_IN_OCTETS, "tx": OID_IF_OUT_OCTETS}

type SwitchConfigEntry = ConfigEntry[SwitchCoordinator]


class SwitchCoordinator(DataUpdateCoordinator[SwitchData]):
    """Poll the switch and compute traffic rates."""

    config_entry: SwitchConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SwitchConfigEntry,
        client: SnmpClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self._v1 = entry.data.get(CONF_VERSION, DEFAULT_VERSION) == VERSION_1
        self._last_poll: float | None = None
        self._uptime = UptimeTracker()
        self._last_ticks: int | None = None
        self._changed: dict[int, tuple[int, datetime]] = {}

    async def _async_update_data(self) -> SwitchData:
        try:
            system = await self.client.get(OID_SYS_UPTIME, OID_SYS_DESCR, OID_SYS_OBJECT_ID)
            tables = await self.client.walk_many(TABLES_V1 if self._v1 else TABLES)
        except SnmpError as err:
            raise UpdateFailed(f"switch did not answer: {err}") from err

        now = time.monotonic()
        # Q-BRIDGE lists the table per VLAN; use the classic table if it is empty.
        fdb = tables["fdb_q"] or tables["fdb"]
        ports = build_ports(tables, fdb, tables["base_port"])
        if not ports:
            raise UpdateFailed("switch returned no ports")

        previous = self.data.ports if self.data else None
        elapsed = now - self._last_poll if self._last_poll is not None else 0
        add_rates(ports, previous, elapsed, 32 if self._v1 else 64)
        self._last_poll = now

        ticks = int(system.get(OID_SYS_UPTIME, 0))
        self._stamp_link_changes(ports, ticks)
        # A reboot resets every ifLastChange: that is no event worth reporting.
        if previous and self._last_ticks is not None and ticks >= self._last_ticks:
            self._fire_link_events(ports, previous)
        self._last_ticks = ticks

        return SwitchData(
            uptime=self._uptime.seconds(ticks),
            description=text(system.get(OID_SYS_DESCR, b"")),
            object_id=text(system.get(OID_SYS_OBJECT_ID, "")),
            ports=ports,
        )

    def _stamp_link_changes(self, ports: dict[int, PortData], ticks: int) -> None:
        """Turn ifLastChange into a time. It is fixed when first seen, so it does not drift."""
        now = dt_util.utcnow()
        for number, port in ports.items():
            known = self._changed.get(number)
            if known is None or known[0] != port.last_change:
                ago = timedelta(seconds=max(ticks - port.last_change, 0) / 100)
                known = (port.last_change, now - ago)
                self._changed[number] = known
            port.link_changed_at = known[1]

    def _fire_link_events(self, ports: dict[int, PortData], previous: dict[int, PortData]) -> None:
        """Fire an event for every port whose link changed since the last poll."""
        registry = er.async_get(self.hass)
        names = self.config_entry.options.get(CONF_PORT_NAMES, {})
        for number, port in ports.items():
            old = previous.get(number)
            if old is None or old.last_change == port.last_change:
                continue
            self.hass.bus.async_fire(
                EVENT_LINK_CHANGED,
                {
                    "entry_id": self.config_entry.entry_id,
                    "switch": self.config_entry.title,
                    "port": number,
                    "port_name": names.get(str(number), ""),
                    "up": port.up,
                    "speed": port.speed,
                    # The link went down and up again between two polls.
                    "flap": port.up == old.up,
                    "entity_id": registry.async_get_entity_id(
                        "binary_sensor", DOMAIN, f"{self.config_entry.unique_id}_port{number}_link"
                    ),
                },
            )
