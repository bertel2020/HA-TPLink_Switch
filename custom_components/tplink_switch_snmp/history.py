"""The data rates of the last days, kept by the integration itself (no recorder needed)."""

from __future__ import annotations

from collections import deque
from typing import Any

# name -> (seconds per value, seconds to keep): 24 hours in five-minute values, 7 days in hours,
# 30 days in two-hour values
RANGES = {"24h": (300, 86400), "7d": (3600, 604800), "30d": (7200, 2592000)}
BUCKET, KEEP = RANGES["24h"]
# keys of the counts, kept like ports (the value is stored as "receive")
COUNT_ACTIVE, COUNT_MACS = 1, 2


class _Tier:
    """The rates of every port, averaged into values of one length."""

    def __init__(self, bucket: int, keep: int) -> None:
        self.bucket = bucket
        self.keep = keep
        # per port: [bucket start, mean receive, mean transmit, number of samples]
        self._ports: dict[int, deque[list[float]]] = {}

    def add(self, now: float, rates: dict[int, tuple[float | None, float | None]]) -> None:
        bucket = int(now // self.bucket * self.bucket)
        for port, (rx, tx) in rates.items():
            if rx is None or tx is None:
                continue
            values = self._ports.setdefault(port, deque())
            if values and values[-1][0] > bucket:
                continue  # the clock went back; keep what is there
            if values and values[-1][0] == bucket:
                last = values[-1]
                count = last[3] + 1
                last[1] += (rx - last[1]) / count
                last[2] += (tx - last[2]) / count
                last[3] = count
            else:
                values.append([bucket, rx, tx, 1])
        self.prune(bucket)

    def prune(self, bucket: int) -> None:
        for port, values in list(self._ports.items()):
            while values and values[0][0] <= bucket - self.keep:
                values.popleft()
            if not values:
                del self._ports[port]

    def series(self, port: int) -> list[tuple[float, float, float]]:
        return [(t, rx, tx) for t, rx, tx, _ in self._ports.get(port, ())]

    def total_series(self) -> list[tuple[float, float, float]]:
        """(bucket start, summed receive, summed transmit) over all ports, oldest first."""
        sums: dict[float, list[float]] = {}
        for values in self._ports.values():
            for t, rx, tx, _ in values:
                total = sums.setdefault(t, [0.0, 0.0])
                total[0] += rx
                total[1] += tx
        return [(t, rx, tx) for t, (rx, tx) in sorted(sums.items())]

    def as_dict(self) -> dict[str, list[list[float]]]:
        return {
            str(port): [[t, round(rx, 3), round(tx, 3), n] for t, rx, tx, n in values]
            for port, values in self._ports.items()
        }

    def load(self, data: Any, now: float) -> None:
        """Take what was stored; anything that does not look right is left out."""
        if not isinstance(data, dict):
            return
        for key, rows in data.items():
            if not str(key).isdigit() or not isinstance(rows, list):
                continue
            values: deque[list[float]] = deque()
            for row in rows:
                try:
                    t, rx, tx, n = (float(x) for x in row)
                except (TypeError, ValueError):
                    continue
                if n >= 1 and (not values or t > values[-1][0]):
                    values.append([t, rx, tx, n])
            if values:
                self._ports[int(key)] = values
        self.prune(int(now // self.bucket * self.bucket))


LINK_WINDOW = 86400  # a link change counts for 24 hours


class LinkLog:
    """When the link of each port changed during the last day (a change is up or down)."""

    def __init__(self) -> None:
        self._events: dict[int, list[float]] = {}

    def add(self, now: float, port: int, times: int = 1) -> None:
        self._events.setdefault(port, []).extend([now] * times)

    def count(self, now: float, port: int) -> int:
        """Changes of a port in the last 24 hours; older ones are dropped."""
        events = [t for t in self._events.get(port, ()) if t > now - LINK_WINDOW]
        if events:
            self._events[port] = events
        else:
            self._events.pop(port, None)
        return len(events)

    def as_dict(self) -> dict[str, list[float]]:
        return {str(port): [round(t, 1) for t in times] for port, times in self._events.items()}

    @classmethod
    def from_dict(cls, data: Any, now: float) -> LinkLog:
        """Restore what was stored; anything that does not look right is left out."""
        log = cls()
        if isinstance(data, dict):
            for key, times in data.items():
                if not str(key).isdigit() or not isinstance(times, list):
                    continue
                kept = [
                    float(t)
                    for t in times
                    if isinstance(t, int | float) and now - LINK_WINDOW < t <= now
                ]
                if kept:
                    log._events[int(key)] = kept
        return log


class RateHistory:
    """Rates per port: five-minute values for a day, hours for a week, two hours for a month."""

    def __init__(self) -> None:
        self._tiers = {name: _Tier(*size) for name, size in RANGES.items()}
        self._counts = {name: _Tier(*size) for name, size in RANGES.items()}

    def add(self, now: float, rates: dict[int, tuple[float | None, float | None]]) -> None:
        """Add the rates of one poll. A poll without both rates (a counter reset) adds nothing."""
        for tier in self._tiers.values():
            tier.add(now, rates)

    def series(self, port: int, range_: str = "24h") -> list[tuple[float, float, float]]:
        """(bucket start, receive, transmit) for a port, oldest first."""
        return self._tiers[range_].series(port)

    def total_series(self, range_: str) -> list[tuple[float, float, float]]:
        """The rates of the whole switch: (bucket start, receive, transmit), oldest first."""
        return self._tiers[range_].total_series()

    def add_counts(self, now: float, active_ports: int, macs: int) -> None:
        """Add how many ports have a link and how many MAC addresses the switch has learned."""
        for tier in self._counts.values():
            tier.add(
                now,
                {COUNT_ACTIVE: (float(active_ports), 0.0), COUNT_MACS: (float(macs), 0.0)},
            )

    def count_series(self, which: int, range_: str) -> list[tuple[float, float]]:
        """(bucket start, value) of the active ports (COUNT_ACTIVE) or the MAC addresses."""
        return [(t, v) for t, v, _ in self._counts[range_].series(which)]

    def as_dict(self) -> dict[str, Any]:
        """What gets stored. "ports" holds the five-minute values, as in the first version."""
        return {
            "ports": self._tiers["24h"].as_dict(),
            "hourly": self._tiers["7d"].as_dict(),
            "two_hourly": self._tiers["30d"].as_dict(),
            "counts": {name: tier.as_dict() for name, tier in self._counts.items()},
        }

    @classmethod
    def from_dict(cls, data: Any, now: float) -> RateHistory:
        """Restore what was stored; an older file without the hours still loads."""
        history = cls()
        if isinstance(data, dict):
            history._tiers["24h"].load(data.get("ports"), now)
            history._tiers["7d"].load(data.get("hourly"), now)
            history._tiers["30d"].load(data.get("two_hourly"), now)
            counts = data.get("counts")
            if isinstance(counts, dict):
                for name, tier in history._counts.items():
                    tier.load(counts.get(name), now)
        return history
