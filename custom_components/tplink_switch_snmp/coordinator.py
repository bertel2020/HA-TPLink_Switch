"""Data update coordinator for the switch."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ADMIN_DOWN,
    ADMIN_UP,
    CONF_PORT_NAMES,
    CONF_PROTECTED_PORTS,
    CONF_SCAN_INTERVAL,
    CONF_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERSION,
    DOMAIN,
    EVENT_DEVICE_MOVED,
    EVENT_LINK_CHANGED,
    OID_BASE_PORT_IF_INDEX,
    OID_FDB,
    OID_FDB_Q,
    OID_IF_ADMIN_STATUS,
    OID_IF_ALIAS,
    OID_IF_HC_IN_OCTETS,
    OID_IF_HC_OUT_OCTETS,
    OID_IF_HC_PACKETS,
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
    OID_IF_PACKETS,
    OID_SYS_CONTACT,
    OID_SYS_DESCR,
    OID_SYS_LOCATION,
    OID_SYS_OBJECT_ID,
    OID_SYS_UPTIME,
    OID_TPLINK_FIRMWARE,
    OID_TPLINK_HARDWARE,
    PROTECTED_MAC_COUNT,
    VERSION_1,
)
from .history import RateHistory
from .model import (
    PortData,
    SwitchData,
    UptimeTracker,
    add_rates,
    build_ports,
    manufacturer,
    split_hardware,
    text,
)
from .snmp import SnmpClient, SnmpError

_LOGGER = logging.getLogger(__name__)

HISTORY_SAVE_DELAY = 300  # seconds between writes of the stored rates

TABLES = {
    "name": OID_IF_NAME,
    "oper": OID_IF_OPER_STATUS,
    "speed": OID_IF_HIGH_SPEED,
    "rx": OID_IF_HC_IN_OCTETS,
    "tx": OID_IF_HC_OUT_OCTETS,
    "rx_err": OID_IF_IN_ERRORS,
    "tx_err": OID_IF_OUT_ERRORS,
    "last_change": OID_IF_LAST_CHANGE,
    "admin": OID_IF_ADMIN_STATUS,
    "alias": OID_IF_ALIAS,
    **OID_IF_HC_PACKETS,
    "rx_disc": OID_IF_IN_DISCARDS,
    "tx_disc": OID_IF_OUT_DISCARDS,
    "fdb_q": OID_FDB_Q,
    "fdb": OID_FDB,
    "base_port": OID_BASE_PORT_IF_INDEX,
}

# SNMPv1 has no 64 bit counters: it reads the 32 bit ones, which wrap quickly.
TABLES_V1 = {**TABLES, "rx": OID_IF_IN_OCTETS, "tx": OID_IF_OUT_OCTETS, **OID_IF_PACKETS}

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
        self.trap_port = 0  # the configured trap port, set by the setup
        # what the options say about writing; a change of any of it reloads the entry
        self.write_key: tuple[bool, str] = (False, "")
        self.history = RateHistory()
        self._info: dict[str, str | None] | None = None
        self._store: Store[dict] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.history")
        self._last_poll: float | None = None
        self._uptime = UptimeTracker()
        self._last_ticks: int | None = None
        self._changed: dict[int, tuple[int, datetime]] = {}

    async def async_load_history(self) -> None:
        """Restore the rates of the last hours, so a restart does not leave a gap."""
        self.history = RateHistory.from_dict(
            await self._store.async_load(), dt_util.utcnow().timestamp()
        )

    async def async_remove_history(self) -> None:
        """Delete the stored rates when the switch is removed."""
        await self._store.async_remove()

    async def _read_info(self, object_id: str) -> dict[str, str | None]:
        """Location, contact, model and versions. They do not change, so they are read once.

        Each value is asked for on its own: with SNMPv1 one unknown value fails the whole
        request, and a switch of another make does not have TP-Link's own values.
        """
        wanted = {"location": OID_SYS_LOCATION, "contact": OID_SYS_CONTACT}
        if manufacturer(object_id) == "TP-Link":
            wanted |= {"hardware": OID_TPLINK_HARDWARE, "firmware": OID_TPLINK_FIRMWARE}
        info: dict[str, str | None] = {}
        for key, oid in wanted.items():
            try:
                value = (await self.client.get(oid)).get(oid)
            except SnmpError:
                value = None
            info[key] = text(value).strip() or None if value is not None else None
        return info

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

        self.history.add(
            dt_util.utcnow().timestamp(),
            {number: (port.rx_rate, port.tx_rate) for number, port in ports.items() if port.up},
        )
        self._store.async_delay_save(self.history.as_dict, HISTORY_SAVE_DELAY)

        if self._info is None:
            self._info = await self._read_info(text(system.get(OID_SYS_OBJECT_ID, "")))
        model, hw_version = split_hardware(self._info.get("hardware") or "")

        data = SwitchData(
            uptime=self._uptime.seconds(ticks),
            description=text(system.get(OID_SYS_DESCR, b"")),
            object_id=text(system.get(OID_SYS_OBJECT_ID, "")),
            ports=ports,
            model=model,
            hw_version=hw_version,
            sw_version=self._info.get("firmware"),
            location=self._info.get("location"),
            contact=self._info.get("contact"),
        )
        if self.data:
            self._fire_move_events(data, self.data)
        return data

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
                    "port_name": self.port_label(number),
                    "up": port.up,
                    "speed": port.speed,
                    # The link went down and up again between two polls.
                    "flap": port.up == old.up,
                    "entity_id": registry.async_get_entity_id(
                        "binary_sensor", DOMAIN, f"{self.config_entry.unique_id}_port{number}_link"
                    ),
                },
            )

    @property
    def can_write(self) -> bool:
        """Whether writing to the switch is switched on in the options."""
        return bool(self.write_key[0])

    def port_label(self, number: int) -> str:
        """The name of a port: the one given in Home Assistant, else the one at the switch."""
        custom = self.config_entry.options.get(CONF_PORT_NAMES, {}).get(str(number), "")
        if custom:
            return custom
        port = self.data.ports.get(number) if self.data else None
        return port.alias if port else ""

    def is_protected(self, number: int) -> bool:
        """A port that must not be switched off: chosen in the options, or an uplink.

        An uplink is a port that has learned many MAC addresses; switching it off can cut
        Home Assistant off from the switch, and with it the way to switch the port on again.
        """
        chosen = {int(n) for n in self.config_entry.options.get(CONF_PROTECTED_PORTS, [])}
        port = self.data.ports.get(number) if self.data else None
        return number in chosen or (port is not None and len(port.macs) >= PROTECTED_MAC_COUNT)

    async def _write(self, oid: str, value: int | str, number: int) -> None:
        if not self.can_write:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="write_off")
        port = self.data.ports.get(number) if self.data else None
        if port is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_port",
                translation_placeholders={"port": str(number)},
            )
        try:
            await self.client.set(f"{oid}.{port.if_index}", value)
        except SnmpError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"port": str(number), "error": str(err)},
            ) from err
        await self.async_request_refresh()

    async def async_set_port_enabled(self, number: int, enabled: bool) -> None:
        """Switch a port on or off (ifAdminStatus)."""
        if not enabled and self.is_protected(number):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="port_protected",
                translation_placeholders={"port": str(number)},
            )
        await self._write(OID_IF_ADMIN_STATUS, ADMIN_UP if enabled else ADMIN_DOWN, number)

    async def async_set_port_alias(self, number: int, name: str) -> None:
        """Give a port a name at the switch (ifAlias)."""
        await self._write(OID_IF_ALIAS, name, number)

    def known_device(self, mac: str) -> dr.DeviceEntry | None:
        """A device of another integration that has this MAC address, if Home Assistant has one."""
        entry_id = self.config_entry.entry_id
        for device in dr.async_get(self.hass).async_get_devices(
            connections={(dr.CONNECTION_NETWORK_MAC, mac)}
        ):
            if device.config_entry_id != entry_id:
                return device
        return None

    def _fire_move_events(self, data: SwitchData, previous: SwitchData) -> None:
        """Fire an event when a device that Home Assistant knows shows up on another port."""
        old = previous.mac_ports
        for mac, number in data.mac_ports.items():
            before = old.get(mac)
            if before is None or before == number:
                continue
            device = self.known_device(mac)
            if device is None:
                continue
            self.hass.bus.async_fire(
                EVENT_DEVICE_MOVED,
                {
                    "entry_id": self.config_entry.entry_id,
                    "switch": self.config_entry.title,
                    "mac": mac,
                    "name": device.name_by_user or device.name,
                    "device_id": device.id,
                    "from_port": before,
                    "from_port_name": self.port_label(before),
                    "to_port": number,
                    "to_port_name": self.port_label(number),
                },
            )
