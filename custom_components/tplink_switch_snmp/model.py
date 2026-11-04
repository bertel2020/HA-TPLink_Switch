"""Turn raw SNMP tables into port data and traffic rates (no Home Assistant)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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
    rx_rate: float | None = None  # Mbit/s
    tx_rate: float | None = None


@dataclass
class SwitchData:
    """One poll of the switch."""

    uptime: int  # seconds
    description: str  # sysDescr
    ports: dict[int, PortData]  # keyed by port number


def text(value: Any) -> str:
    """Decode an SNMP octet string that holds text."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
    for suffix, name in tables["name"].items():
        name = text(name)
        match = PORT_NAME.match(name)
        if match is None or not suffix.isdigit():
            continue
        if_index = int(suffix)
        number = int(match.group(1))
        up = tables["oper"].get(suffix) == OPER_UP
        ports[number] = PortData(
            if_index=if_index,
            number=number,
            name=name,
            up=up,
            speed=int(tables["speed"].get(suffix, 0)) if up else 0,
            rx_bytes=int(tables["rx"].get(suffix, 0)),
            tx_bytes=int(tables["tx"].get(suffix, 0)),
            rx_errors=int(tables["rx_err"].get(suffix, 0)),
            tx_errors=int(tables["tx_err"].get(suffix, 0)),
            macs=sorted(macs_by_if.get(if_index, ())),
        )
    return ports


def add_rates(
    ports: dict[int, PortData],
    previous: dict[int, PortData] | None,
    seconds: float,
) -> None:
    """Fill rx_rate and tx_rate (Mbit/s) from the change since the last poll."""
    if not previous or seconds <= 0:
        return
    for number, port in ports.items():
        old = previous.get(number)
        if old is None:
            continue
        # A counter that went backwards means the switch was reset: skip once.
        if port.rx_bytes >= old.rx_bytes:
            port.rx_rate = round((port.rx_bytes - old.rx_bytes) * 8 / seconds / 1e6, 3)
        if port.tx_bytes >= old.tx_bytes:
            port.tx_rate = round((port.tx_bytes - old.tx_bytes) * 8 / seconds / 1e6, 3)
