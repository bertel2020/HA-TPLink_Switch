"""Data update coordinator for the switch."""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERSION,
    DOMAIN,
    OID_BASE_PORT_IF_INDEX,
    OID_FDB,
    OID_FDB_Q,
    OID_IF_HC_IN_OCTETS,
    OID_IF_HC_OUT_OCTETS,
    OID_IF_HIGH_SPEED,
    OID_IF_IN_ERRORS,
    OID_IF_IN_OCTETS,
    OID_IF_NAME,
    OID_IF_OPER_STATUS,
    OID_IF_OUT_ERRORS,
    OID_IF_OUT_OCTETS,
    OID_SYS_DESCR,
    OID_SYS_OBJECT_ID,
    OID_SYS_UPTIME,
    VERSION_1,
)
from .model import SwitchData, UptimeTracker, add_rates, build_ports, text
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
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self._v1 = entry.data.get(CONF_VERSION, DEFAULT_VERSION) == VERSION_1
        self._last_poll: float | None = None
        self._uptime = UptimeTracker()

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

        return SwitchData(
            uptime=self._uptime.seconds(int(system.get(OID_SYS_UPTIME, 0))),
            description=text(system.get(OID_SYS_DESCR, b"")),
            object_id=text(system.get(OID_SYS_OBJECT_ID, "")),
            ports=ports,
        )
