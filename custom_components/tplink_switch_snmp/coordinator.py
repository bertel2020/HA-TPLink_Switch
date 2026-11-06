"""Data update coordinator for the switch."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er, issue_registry as ir
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
    EVENT_ALARM,
    EVENT_DEVICE_MOVED,
    EVENT_LINK_CHANGED,
    EXTRA_TABLES,
    OID_BASE_PORT_IF_INDEX,
    OID_ENT_FIRMWARE,
    OID_ENT_HARDWARE,
    OID_ENT_MAKER,
    OID_ENT_MODEL,
    OID_ENT_SOFTWARE,
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
    OID_REBOOT,
    OID_SAVE_CONFIG,
    OID_SYS_CONTACT,
    OID_SYS_DESCR,
    OID_SYS_LOCATION,
    OID_SYS_OBJECT_ID,
    OID_SYS_UPTIME,
    OID_TPLINK_FIRMWARE,
    OID_TPLINK_HARDWARE,
    PROTECTED_MAC_COUNT,
    RMON_TABLES,
    STP_TABLES,
    TRAP_ALARMS,
    VERSION_1,
    VLAN_TABLES,
)
from .history import LinkLog, RateHistory
from .model import (
    PortData,
    SwitchData,
    UptimeTracker,
    add_arp,
    add_config,
    add_error_details,
    add_features,
    add_igmp,
    add_isolation,
    add_loops,
    add_mirror,
    add_qos,
    add_rates,
    add_security,
    add_storm,
    add_stp,
    add_vlans,
    build_ports,
    maker_from_description,
    manufacturer,
    split_hardware,
    text,
)
from .snmp import SnmpClient, SnmpError

_LOGGER = logging.getLogger(__name__)

UNREACHABLE_AFTER = 600  # seconds without an answer before a repair issue is raised
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
        self.selection: object = None  # which entities the options asked for, set by the setup
        self.history = RateHistory()
        self.link_log = LinkLog()
        self._failing_since: datetime | None = None
        self._info: dict[str, str | None] | None = None
        self._store: Store[dict] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.history")
        self._last_poll: float | None = None
        self._uptime = UptimeTracker()
        self._last_ticks: int | None = None
        self._changed: dict[int, tuple[int, datetime]] = {}

    async def async_load_history(self) -> None:
        """Restore the rates of the last hours, so a restart does not leave a gap."""
        stored = await self._store.async_load()
        now = dt_util.utcnow().timestamp()
        self.history = RateHistory.from_dict(stored, now)
        self.link_log = LinkLog.from_dict(
            stored.get("link_changes") if isinstance(stored, dict) else None, now
        )

    async def _read_info(self, object_id: str, description: str) -> dict[str, str | None]:
        """Location, contact, maker, model and versions. They do not change, so they are read once.

        Each value is asked for on its own: with SNMPv1 one unknown value fails the whole
        request, and a switch of another make does not have TP-Link's own values. The standard
        ENTITY-MIB is tried for every switch; TP-Link's own values fill what it leaves empty.
        """
        wanted = {
            "location": OID_SYS_LOCATION,
            "contact": OID_SYS_CONTACT,
            "ent_maker": OID_ENT_MAKER,
            "ent_model": OID_ENT_MODEL,
            "ent_hardware": OID_ENT_HARDWARE,
            "ent_firmware": OID_ENT_FIRMWARE,
            "ent_software": OID_ENT_SOFTWARE,
        }
        if manufacturer(object_id) == "TP-Link":
            wanted |= {"hardware": OID_TPLINK_HARDWARE, "firmware": OID_TPLINK_FIRMWARE}
        info: dict[str, str | None] = {}
        for key, oid in wanted.items():
            try:
                value = (await self.client.get(oid)).get(oid)
            except SnmpError:
                value = None
            info[key] = text(value).strip() or None if value is not None else None
        # the standard answers fill the gaps of TP-Link's own
        if not info.get("hardware") and info["ent_model"]:
            version = info["ent_hardware"]
            info["hardware"] = f"{info['ent_model']} {version}" if version else info["ent_model"]
        info["firmware"] = info.get("firmware") or info["ent_software"] or info["ent_firmware"]
        info["maker"] = (
            manufacturer(object_id) or maker_from_description(description) or info["ent_maker"]
        )
        return info

    async def _read_extras(self, tables: dict[str, str]) -> dict[str, dict[str, Any]]:
        """Optional tables. A switch without one of them just leaves it out."""
        results = await asyncio.gather(
            *(self.client.walk_many({key: oid}) for key, oid in tables.items()),
            return_exceptions=True,
        )
        extras: dict[str, dict[str, Any]] = {}
        for key, result in zip(tables, results, strict=True):
            if isinstance(result, SnmpError):
                continue
            if isinstance(result, BaseException):
                raise result
            extras[key] = result.get(key, {})
        return extras

    async def _async_update_data(self) -> SwitchData:
        try:
            system = await self.client.get(OID_SYS_UPTIME, OID_SYS_DESCR, OID_SYS_OBJECT_ID)
            tables = await self.client.walk_many(TABLES_V1 if self._v1 else TABLES)
        except SnmpError as err:
            self._note_failure()
            raise UpdateFailed(f"switch did not answer: {err}") from err

        self._note_success()

        now = time.monotonic()
        # Q-BRIDGE lists the table per VLAN; use the classic table if it is empty.
        fdb = tables["fdb_q"] or tables["fdb"]
        ports = build_ports(tables, fdb, tables["base_port"])
        if not ports:
            raise UpdateFailed("switch returned no ports")

        previous = self.data.ports if self.data else None
        elapsed = now - self._last_poll if self._last_poll is not None else 0
        add_rates(ports, previous, elapsed, 32 if self._v1 else 64)
        add_error_details(ports, await self._read_extras(RMON_TABLES))
        stp_changes, stp_root_port = add_stp(
            ports, await self._read_extras(STP_TABLES), tables["base_port"]
        )
        vlans = add_vlans(ports, await self._read_extras(VLAN_TABLES), tables["base_port"])
        features: dict[str, bool] = {}
        qos_mode: str | None = None
        mirror: list[dict[str, Any]] = []
        if manufacturer(text(system.get(OID_SYS_OBJECT_ID, ""))) == "TP-Link":
            extras = await self._read_extras(EXTRA_TABLES)
            features = add_features(ports, extras)
            mirror = add_mirror(ports, extras)
            add_isolation(ports, extras)
            add_igmp(ports, extras)
            qos_mode = add_qos(ports, extras)
            add_loops(ports, extras)
            add_config(ports, extras)
            add_security(ports, extras)
            add_storm(ports, extras)
            add_arp(ports, extras)
        self._last_poll = now

        ticks = int(system.get(OID_SYS_UPTIME, 0))
        self._stamp_link_changes(ports, ticks)
        # A reboot resets every ifLastChange: that is no event worth reporting.
        if previous and self._last_ticks is not None and ticks >= self._last_ticks:
            self._fire_link_events(ports, previous)
        self._last_ticks = ticks
        stamp = dt_util.utcnow().timestamp()
        for number, port in ports.items():
            port.link_changes = self.link_log.count(stamp, number)

        self.history.add(
            dt_util.utcnow().timestamp(),
            {number: (port.rx_rate, port.tx_rate) for number, port in ports.items() if port.up},
        )
        self._store.async_delay_save(self._stored, HISTORY_SAVE_DELAY)

        if self._info is None:
            self._info = await self._read_info(
                text(system.get(OID_SYS_OBJECT_ID, "")), text(system.get(OID_SYS_DESCR, b""))
            )
        model, hw_version = split_hardware(self._info.get("hardware") or "")

        data = SwitchData(
            uptime=self._uptime.seconds(ticks),
            description=text(system.get(OID_SYS_DESCR, b"")),
            object_id=text(system.get(OID_SYS_OBJECT_ID, "")),
            ports=ports,
            manufacturer=self._info.get("maker"),
            model=model,
            hw_version=hw_version,
            sw_version=self._info.get("firmware"),
            location=self._info.get("location"),
            contact=self._info.get("contact"),
            stp_changes=stp_changes,
            stp_root_port=stp_root_port,
            vlans=vlans,
            features=features,
            mirror=mirror,
            qos_mode=qos_mode,
        )
        if self.data:
            self._fire_move_events(data, self.data)
            self._fire_arp_events(data, self.data)
            if (
                data.stp_changes is not None
                and self.data.stp_changes is not None
                and data.stp_changes > self.data.stp_changes
            ):
                self._fire_alarm_event("stp_topology_change")
        return data

    def _stored(self) -> dict[str, Any]:
        """What is kept on disk: the rates and the link changes of the last day."""
        return {**self.history.as_dict(), "link_changes": self.link_log.as_dict()}

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
            # a link that went down and up between two polls changed twice
            self.link_log.add(dt_util.utcnow().timestamp(), number, 1 if port.up != old.up else 2)
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

    def fire_alarm(self, trap: str | None) -> None:
        """Fire an event if the trap is one of the alarms the switch reports on its own."""
        alarm = TRAP_ALARMS.get(trap or "")
        if alarm is not None:
            self._fire_alarm_event(alarm)

    def _fire_arp_events(self, data: SwitchData, previous: SwitchData) -> None:
        """Fire an alarm for each port that has seen illegal ARP packets since the last poll."""
        for number, port in data.ports.items():
            old = previous.ports.get(number)
            if port.arp_illegal is None or old is None or old.arp_illegal is None:
                continue
            if port.arp_illegal > old.arp_illegal:
                self._fire_alarm_event(
                    "arp_illegal",
                    port=number,
                    port_name=self.port_label(number),
                    count=port.arp_illegal - old.arp_illegal,
                )

    def _fire_alarm_event(self, alarm: str, **details: Any) -> None:
        self.hass.bus.async_fire(
            EVENT_ALARM,
            {
                "entry_id": self.config_entry.entry_id,
                "switch": self.config_entry.title,
                "alarm": alarm,
                **details,
            },
        )

    @property
    def can_write(self) -> bool:
        """Whether writing to the switch is switched on in the options."""
        return bool(self.write_key[0])

    @property
    def can_act(self) -> bool:
        """Whether the switch can be told to save or restart: a TP-Link, with writing on."""
        return self.can_write and manufacturer(self.data.object_id) == "TP-Link"

    def port_label(self, number: int) -> str:
        """The name of a port: the one given in Home Assistant, else the one at the switch."""
        custom: str = self.config_entry.options.get(CONF_PORT_NAMES, {}).get(str(number), "")
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

    async def _act(self, oid: str, action: str) -> None:
        """Write 1 to a TP-Link object that does something when it is set."""
        if not self.can_write:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="write_off")
        try:
            await self.client.set(oid, 1)
        except SnmpError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_failed",
                translation_placeholders={"action": action, "error": str(err)},
            ) from err

    async def async_save_config(self) -> None:
        """Write the running configuration of the switch to its flash."""
        await self._act(OID_SAVE_CONFIG, "save")

    async def async_reboot(self) -> None:
        """Restart the switch. It does not answer for a while, so there is no refresh."""
        await self._act(OID_REBOOT, "reboot")

    @property
    def _issue_id(self) -> str:
        return f"unreachable_{self.config_entry.entry_id}"

    def _note_failure(self) -> None:
        """Raise a repair issue once the switch has been silent for a while."""
        now = dt_util.utcnow()
        if self._failing_since is None:
            self._failing_since = now
        if (now - self._failing_since).total_seconds() >= UNREACHABLE_AFTER:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="unreachable",
                translation_placeholders={
                    "name": self.config_entry.title,
                    "host": self.config_entry.data[CONF_HOST],
                },
            )

    def _note_success(self) -> None:
        """The switch answers: the issue is over."""
        if self._failing_since is not None:
            self._failing_since = None
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)

    def clear_issue(self) -> None:
        """Take the issue away, e.g. when the switch is removed."""
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)

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
