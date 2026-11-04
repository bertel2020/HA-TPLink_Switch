"""Turn raw SNMP tables into port data and traffic rates (no Home Assistant)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any

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
    link_changed_at: datetime | None = None


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
