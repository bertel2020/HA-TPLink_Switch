"""Turn raw SNMP tables into port data and traffic rates (no Home Assistant)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any

from .const import (
    ADMIN_DOWN,
    ADMIN_UP,
    ERROR_DETAILS,
    FEATURES,
    IGMP_COUNTERS,
    PORT_MODES,
    QOS_MODES,
    STORM_LIMITS,
    STP_STATES,
)

PORT_LIST_MAX = 128  # no switch has more ports than this
PORT_NAME = re.compile(r"^port\s*(\d+)", re.IGNORECASE)
OPER_UP = 1


@dataclass
class PortData:
    """State of one physical port."""

    if_index: int
    number: int
    name: str
    up: bool
    speed: int  # Mbit/s, 0 without link
    rx_bytes: int
    tx_bytes: int
    rx_errors: int
    tx_errors: int
    macs: list[str] = field(default_factory=list)
    rx_pkts: int = 0  # all packets in and out: unicast, multicast and broadcast
    tx_pkts: int = 0
    rx_mcast: int = 0
    rx_bcast: int = 0
    rx_discards: int = 0
    tx_discards: int = 0
    rx_rate: float | None = None  # Mbit/s
    tx_rate: float | None = None
    rx_pps: float | None = None  # packets per second
    tx_pps: float | None = None
    rx_mcast_pps: float | None = None
    rx_bcast_pps: float | None = None
    rx_util: float | None = None  # percent of the link speed
    tx_util: float | None = None
    last_change: int = 0  # ifLastChange: sysUpTime ticks of the last link change
    admin_up: bool = True  # the port is switched on (a switched-off port has no link)
    alias: str = ""  # the name given to the port at the switch (ifAlias)
    link_changed_at: datetime | None = None
    loop: bool | None = None  # a loop is detected here; None if the port is not watched
    loop_blocked: bool | None = None  # the switch has blocked the port because of a loop
    mode: str | None = None  # how the port is set: "auto", "100full", ... (None if unknown)
    flow_control: bool | None = None
    lag: str | None = None  # the link aggregation group the port belongs to
    security_max: int | None = None  # port security: most MAC addresses the port may learn
    security_learned: int | None = None  # ... and how many it has learned (None: not on)
    storm: dict[str, int] = field(default_factory=dict)  # storm control limits in kbit/s
    error_details: dict[str, int] = field(default_factory=dict)  # RMON: CRC, collisions ...
    stp_state: str | None = None  # spanning tree: "forwarding", "blocking", ...
    arp_illegal: int | None = None  # illegal ARP packets seen (the switch's ARP protection)
    arp_trusted: bool | None = None  # the port is trusted by the ARP protection
    dhcp_trusted: bool | None = None  # DHCP snooping is on and the port is a trusted one
    qos_priority: int | None = None  # the CoS that frames of this port get (0 to 7)
    igmp: dict[str, int] = field(default_factory=dict)  # IGMP snooping packets seen
    igmp_snooping: bool | None = None  # IGMP snooping is on at this port
    mirror: str | None = None  # port mirroring: "monitor" (gets the copies) or "source"
    isolated: bool | None = None  # the port cannot reach all the other ports (port isolation)
    isolation_forward: list[int] | None = None  # the ports it can reach, if the switch says
    pvid: int | None = None  # the VLAN that untagged frames at this port belong to
    vlans_untagged: list[int] = field(default_factory=list)  # VLANs sent without a tag
    vlans_tagged: list[int] = field(default_factory=list)  # VLANs sent with a tag


@dataclass
class SwitchData:
    """One poll of the switch."""

    uptime: int  # seconds
    description: str  # sysDescr
    object_id: str  # sysObjectID
    ports: dict[int, PortData]  # keyed by port number
    model: str | None = None
    hw_version: str | None = None
    sw_version: str | None = None
    location: str | None = None
    contact: str | None = None
    stp_changes: int | None = None  # how often the spanning tree topology has changed
    stp_root_port: int | None = None  # the port that leads to the root bridge
    vlans: dict[int, str] = field(default_factory=dict)  # VLAN ID -> name
    features: dict[str, bool] = field(default_factory=dict)  # FEATURES name -> switched on
    mirror: list[dict[str, Any]] = field(default_factory=list)  # the mirror groups that are on
    qos_mode: str | None = None  # how the queues are served: "sp", "wrr", "sp_wrr", "equal"

    @property
    def mac_ports(self) -> dict[str, int]:
        """The port each learned MAC address was seen on."""
        return {mac: number for number, port in sorted(self.ports.items()) for mac in port.macs}


# Enterprise numbers (the number after 1.3.6.1.4.1 in sysObjectID) of known makers.
ENTERPRISES = {11863: "TP-Link"}


def manufacturer(object_id: str) -> str | None:
    """The maker named by the enterprise number in sysObjectID, if it is a known one."""
    parts = object_id.strip(".").split(".")
    if parts[:6] == ["1", "3", "6", "1", "4", "1"] and len(parts) > 6 and parts[6].isdigit():
        return ENTERPRISES.get(int(parts[6]))
    return None


def text(value: Any) -> str:
    """Decode an SNMP octet string that holds text."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


TICKS_WRAP = 2**32  # sysUpTime counts hundredths of a second in 32 bits
# A drop is a wrap and not a reboot if the last value was this close to the limit (one hour).
WRAP_WINDOW = 360_000


class UptimeTracker:
    """Uptime in seconds that carries on past the 497 days after which sysUpTime wraps."""

    def __init__(self) -> None:
        self._last: int | None = None
        self._wraps = 0

    def seconds(self, ticks: int) -> int:
        """The uptime for the latest sysUpTime reading."""
        if self._last is not None and ticks < self._last:
            if self._last > TICKS_WRAP - WRAP_WINDOW:
                self._wraps += 1
            else:
                self._wraps = 0  # the counter fell from somewhere low: a reboot
        self._last = ticks
        return (self._wraps * TICKS_WRAP + ticks) // 100


_VERSION = re.compile(r"^v?\d+(\.\d+)*$")


def split_hardware(value: str) -> tuple[str | None, str | None]:
    """Model and hardware version from a string like "TL-SG3424 1.0"."""
    value = value.strip()
    if not value:
        return None, None
    head, _, tail = value.rpartition(" ")
    if head and _VERSION.match(tail):
        return head, tail.lstrip("v")
    return value, None


def format_mac(raw: bytes | str) -> str:
    """Format six bytes as aa:bb:cc:dd:ee:ff."""
    if isinstance(raw, str):
        return raw.lower()
    return ":".join(f"{b:02x}" for b in raw)


def mac_from_suffix(suffix: str) -> str | None:
    """The last six numbers of a forwarding table index are the MAC address."""
    parts = suffix.split(".")[-6:]
    if len(parts) != 6:
        return None
    try:
        return ":".join(f"{int(p):02x}" for p in parts)
    except ValueError:
        return None


def _count(tables: dict[str, dict[str, Any]], suffix: str, key: str) -> int:
    """A counter of one interface; 0 if the switch does not have that column."""
    return int(tables.get(key, {}).get(suffix, 0))


def _physical_ports(names: dict[str, Any], base_port_to_if: dict[str, Any]) -> dict[int, int]:
    """Map ifIndex to port number for the physical ports.

    The bridge port table lists exactly the interfaces that forward traffic, so the VLAN,
    loopback and management interfaces are not in it, whatever the model calls its ports.
    Without that table, fall back to the "port N" names of the JetStream firmware.
    """
    if base_port_to_if:
        return {
            int(if_index): int(base_port)
            for base_port, if_index in base_port_to_if.items()
            if base_port.isdigit() and isinstance(if_index, int)
        }
    ports = {}
    for suffix, name in names.items():
        match = PORT_NAME.match(text(name))
        if match and suffix.isdigit():
            ports[int(suffix)] = int(match.group(1))
    return ports


def build_ports(
    tables: dict[str, dict[str, Any]],
    fdb: dict[str, Any],
    base_port_to_if: dict[str, Any],
) -> dict[int, PortData]:
    """Combine the interface tables and the forwarding table into ports."""
    macs_by_if: dict[int, set[str]] = {}
    for suffix, base_port in fdb.items():
        mac = mac_from_suffix(suffix)
        if mac is None or not isinstance(base_port, int):
            continue
        if_index = base_port_to_if.get(str(base_port), base_port)
        if isinstance(if_index, int):
            macs_by_if.setdefault(if_index, set()).add(mac)

    ports: dict[int, PortData] = {}
    for if_index, number in sorted(_physical_ports(tables["name"], base_port_to_if).items()):
        suffix = str(if_index)
        if suffix not in tables["oper"]:
            continue  # listed as a port but not present in the interface table
        up = tables["oper"][suffix] == OPER_UP

        ports[number] = PortData(
            if_index=if_index,
            number=number,
            name=text(tables["name"].get(suffix, f"port {number}")),
            up=up,
            speed=int(tables["speed"].get(suffix, 0)) if up else 0,
            rx_bytes=int(tables["rx"].get(suffix, 0)),
            tx_bytes=int(tables["tx"].get(suffix, 0)),
            rx_errors=int(tables["rx_err"].get(suffix, 0)),
            tx_errors=int(tables["tx_err"].get(suffix, 0)),
            admin_up=tables.get("admin", {}).get(suffix, ADMIN_UP) != ADMIN_DOWN,
            alias=text(tables.get("alias", {}).get(suffix, b"")).strip(),
            last_change=int(tables.get("last_change", {}).get(suffix, 0)),
            rx_pkts=_count(tables, suffix, "rx_uc")
            + _count(tables, suffix, "rx_mc")
            + _count(tables, suffix, "rx_bc"),
            tx_pkts=_count(tables, suffix, "tx_uc")
            + _count(tables, suffix, "tx_mc")
            + _count(tables, suffix, "tx_bc"),
            rx_mcast=_count(tables, suffix, "rx_mc"),
            rx_bcast=_count(tables, suffix, "rx_bc"),
            rx_discards=int(tables.get("rx_disc", {}).get(suffix, 0)),
            tx_discards=int(tables.get("tx_disc", {}).get(suffix, 0)),
            macs=sorted(macs_by_if.get(if_index, ())),
        )
    return ports


_NO = ("no", "not", "normal", "none", "false", "off", "disable", "free", "-")


def flag(value: Any) -> bool:
    """Whether a state of the switch (a number or a text like "Loop" or "No Loop") is set."""
    if isinstance(value, int):
        return value != 0
    word = text(value).strip().lower()
    return bool(word) and word != "0" and not word.startswith(_NO)


def add_loops(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in loop detection from TP-Link's table; ports it does not watch stay None."""
    looped = extras.get("loop", {})
    for number, port in ports.items():
        suffix = str(number)
        if suffix not in looped:
            continue
        if extras.get("loop_on") and extras["loop_on"].get(suffix) != 1:
            continue  # detection is switched off at this port
        port.loop = flag(looped[suffix])
        if suffix in extras.get("loop_blocked", {}):
            port.loop_blocked = flag(extras["loop_blocked"][suffix])


def add_config(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in how the ports are set (speed and duplex, flow control, trunk)."""
    for number, port in ports.items():
        suffix = str(number)
        mode = extras.get("cfg_mode", {}).get(suffix)
        if isinstance(mode, int):
            port.mode = PORT_MODES.get(mode)
        flow = extras.get("cfg_flow", {}).get(suffix)
        if isinstance(flow, int):
            port.flow_control = flow == 1
        lag = text(extras.get("cfg_lag", {}).get(suffix, b"")).strip()
        # the switch writes "N/A" (or dashes) for a port that is in no trunk
        port.lag = lag if lag.strip("-") and lag.upper() != "N/A" else None


def add_security(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in port security for the ports where the switch has it switched on."""
    for number, port in ports.items():
        suffix = str(number)
        maximum = extras.get("sec_max", {}).get(suffix)
        learned = extras.get("sec_learned", {}).get(suffix)
        if extras.get("sec_on", {}).get(suffix) == 1 and isinstance(maximum, int):
            port.security_max = maximum
            port.security_learned = learned if isinstance(learned, int) else None


def add_error_details(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in the RMON counters of each port that has a row in the statistics table."""
    by_if = {port.if_index: port for port in ports.values()}
    for row, source in extras.get("rmon_source", {}).items():
        # etherStatsDataSource is an OID that ends in the ifIndex; without it the row is the port
        last = text(source).rsplit(".", 1)[-1]
        if_index = int(last) if last.isdigit() else int(row) if row.isdigit() else None
        port = by_if.get(if_index) if if_index is not None else None
        if port is None:
            continue
        for kind, column in ERROR_DETAILS.items():
            value = extras.get(column, {}).get(row)
            if isinstance(value, int):
                port.error_details[kind] = value


def add_stp(
    ports: dict[int, PortData],
    extras: dict[str, dict[str, Any]],
    base_port_to_if: dict[str, Any],
) -> tuple[int | None, int | None]:
    """Fill in the spanning tree state of the ports.

    Returns how often the topology has changed and the port that leads to the root bridge;
    each is None if the switch does not say.
    """
    by_if = {port.if_index: port for port in ports.values()}

    def port_of(base_port: Any) -> PortData | None:
        if_index = base_port_to_if.get(str(base_port), base_port)
        return by_if.get(int(if_index)) if str(if_index).isdigit() else None

    for base_port, value in extras.get("stp_state", {}).items():
        port = port_of(base_port)
        if port is not None and isinstance(value, int) and value in STP_STATES:
            port.stp_state = STP_STATES[value]

    changes = extras.get("stp_changes", {}).get("0")
    root = extras.get("stp_root_port", {}).get("0")
    root_port = port_of(root) if isinstance(root, int) and root > 0 else None
    return (
        changes if isinstance(changes, int) else None,
        root_port.number if root_port else None,
    )


def add_arp(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in the ARP protection counters, if the switch has that protection switched on."""
    enabled = extras.get("arp_on", {})
    if enabled and enabled.get("0") != 1:
        return
    for number, port in ports.items():
        illegal = extras.get("arp_illegal", {}).get(str(number))
        if isinstance(illegal, int):
            port.arp_illegal = illegal
            state = extras.get("arp_state", {}).get(str(number))
            port.arp_trusted = state == 1 if isinstance(state, int) else None


def bitmap_ports(bits: Any) -> set[int]:
    """The bridge ports set in a PortList: the first bit of the first byte is port 1."""
    if not isinstance(bits, bytes):
        return set()
    return {
        index * 8 + bit + 1
        for index, byte in enumerate(bits)
        for bit in range(8)
        if byte & (0x80 >> bit)
    }


def add_vlans(
    ports: dict[int, PortData],
    extras: dict[str, dict[str, Any]],
    base_port_to_if: dict[str, Any],
) -> dict[int, str]:
    """Fill in the PVID and the VLAN membership of the ports; returns the VLAN names."""
    by_if = {port.if_index: port for port in ports.values()}

    def port_of(base_port: int | str) -> PortData | None:
        if_index = base_port_to_if.get(str(base_port), base_port)
        return by_if.get(int(if_index)) if str(if_index).isdigit() else None

    for base_port, pvid in extras.get("vlan_pvid", {}).items():
        port = port_of(base_port)
        if port is not None and isinstance(pvid, int):
            port.pvid = pvid

    names: dict[int, str] = {}
    for key, name in extras.get("vlan_name", {}).items():
        if not key.isdigit():
            continue
        vlan = int(key)
        names[vlan] = text(name)
        untagged = bitmap_ports(extras.get("vlan_untagged", {}).get(key))
        for member in bitmap_ports(extras.get("vlan_egress", {}).get(key)):
            port = port_of(member)
            if port is not None:
                (port.vlans_untagged if member in untagged else port.vlans_tagged).append(vlan)
    return names


def add_igmp(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in the IGMP snooping packet counters of each port that has a row for them."""
    for number, port in ports.items():
        suffix = str(number)
        for key, columns in IGMP_COUNTERS.items():
            values = [
                value
                for column in columns
                if isinstance(value := extras.get(column, {}).get(suffix), int)
            ]
            if values:
                port.igmp[key.removeprefix("igmp_")] = sum(values)
        enabled = extras.get("igmp_port_on", {}).get(suffix)
        port.igmp_snooping = enabled == 1 if isinstance(enabled, int) else None


def add_qos(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> str | None:
    """Fill in the QoS priority of the ports; returns how the queues are served."""
    for number, port in ports.items():
        priority = extras.get("qos_priority", {}).get(str(number))
        if isinstance(priority, int):
            port.qos_priority = priority
    mode = extras.get("qos_mode", {}).get("0")
    return QOS_MODES.get(mode) if isinstance(mode, int) else None


def port_list(value: Any) -> set[int]:
    """The ports of a list like "1-5,9-11,16" (or "1/0/1-1/0/3": the last number counts)."""
    ports: set[int] = set()
    for part in text(value).split(","):
        ends = [int(numbers[-1]) for end in part.split("-") if (numbers := re.findall(r"\d+", end))]
        if len(ends) == 2 and 0 < ends[0] <= ends[1] <= PORT_LIST_MAX:
            ports.update(range(ends[0], ends[1] + 1))
        elif len(ends) == 1:
            ports.add(ends[0])
    return ports


def add_mirror(
    ports: dict[int, PortData], extras: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Mark the ports of port mirroring; returns the mirror groups that are on."""
    groups = []
    for group, state in extras.get("mirror_state", {}).items():
        if state != 1:
            continue
        monitor = extras.get("mirror_monitor", {}).get(group)
        monitor_port = (
            monitor if isinstance(monitor, int) else min(port_list(monitor), default=None)
        )
        sources = {
            "ingress": sorted(port_list(extras.get("mirror_in", {}).get(group, b""))),
            "egress": sorted(port_list(extras.get("mirror_out", {}).get(group, b""))),
        }
        groups.append({"group": group, "monitor": monitor_port, **sources})
        if monitor_port in ports:
            ports[monitor_port].mirror = "monitor"
        for number in {*sources["ingress"], *sources["egress"]} & ports.keys():
            ports[number].mirror = ports[number].mirror or "source"
    return groups


def add_isolation(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in which ports a port can reach; an empty list is taken as "not set"."""
    for number, port in ports.items():
        raw = extras.get("isolation", {}).get(str(number))
        forward = port_list(raw) if raw is not None else set()
        if not forward:
            continue
        port.isolation_forward = sorted(forward)
        port.isolated = not (ports.keys() - {number}) <= forward


def add_features(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> dict[str, bool]:
    """Which of the functions of the switch are on; the ports of DHCP snooping get their trust."""
    features = {
        name: value == 1
        for name, (_, table) in FEATURES.items()
        if isinstance(value := extras.get(table, {}).get("0"), int)
    }
    if extras.get("mirror_state"):
        features["mirror"] = any(state == 1 for state in extras["mirror_state"].values())
    if features.get("dhcp"):
        for number, port in ports.items():
            trust = extras.get("dhcp_trust", {}).get(str(number))
            if isinstance(trust, int):
                port.dhcp_trusted = trust == 1
    return features


STORM_KINDS = {"storm_bc": "broadcast", "storm_mc": "multicast", "storm_ul": "unicast"}


def add_storm(ports: dict[int, PortData], extras: dict[str, dict[str, Any]]) -> None:
    """Fill in the storm control limits; a kind that is off is left out."""
    for number, port in ports.items():
        for key, kind in STORM_KINDS.items():
            limit = STORM_LIMITS.get(extras.get(key, {}).get(str(number), 0))
            if limit:
                port.storm[kind] = limit


def _delta(new: int, old: int, bits: int) -> int | None:
    """How far a counter advanced; None if it went backwards and cannot be a wrap."""
    if new >= old:
        return new - old
    # A 32 bit counter wraps every 34 seconds at 1 Gbit/s, so a drop is a wrap there.
    # A 64 bit counter never does: a drop means the switch was reset.
    return new + 2**32 - old if bits == 32 else None


def utilization(rate: float | None, speed: int) -> float | None:
    """The share of the link speed in percent; None without a rate or a link."""
    if rate is None or speed <= 0:
        return None
    return round(min(rate / speed * 100, 100.0), 1)


def _per_second(new: int, old: int, seconds: float, bits: int) -> float | None:
    delta = _delta(new, old, bits)
    return None if delta is None else round(delta / seconds, 1)


def add_rates(
    ports: dict[int, PortData],
    previous: dict[int, PortData] | None,
    seconds: float,
    counter_bits: int = 64,
) -> None:
    """Fill rx_rate and tx_rate (Mbit/s) from the change since the last poll."""
    if not previous or seconds <= 0:
        return
    for number, port in ports.items():
        old = previous.get(number)
        if old is None:
            continue
        rx = _delta(port.rx_bytes, old.rx_bytes, counter_bits)
        tx = _delta(port.tx_bytes, old.tx_bytes, counter_bits)
        if rx is not None:
            port.rx_rate = round(rx * 8 / seconds / 1e6, 3)
        if tx is not None:
            port.tx_rate = round(tx * 8 / seconds / 1e6, 3)
        port.rx_pps = _per_second(port.rx_pkts, old.rx_pkts, seconds, counter_bits)
        port.tx_pps = _per_second(port.tx_pkts, old.tx_pkts, seconds, counter_bits)
        port.rx_mcast_pps = _per_second(port.rx_mcast, old.rx_mcast, seconds, counter_bits)
        port.rx_bcast_pps = _per_second(port.rx_bcast, old.rx_bcast, seconds, counter_bits)
        port.rx_util = utilization(port.rx_rate, port.speed)
        port.tx_util = utilization(port.tx_rate, port.speed)
