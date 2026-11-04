"""The data rates of the last 24 hours, kept by the integration itself (no recorder needed)."""

from __future__ import annotations

from collections import deque
from typing import Any

BUCKET = 300  # seconds per value: 288 values cover 24 hours
KEEP = 86400  # seconds to keep


class RateHistory:
    """Receive and transmit rate per port, averaged into five-minute values."""

    def __init__(self) -> None:
        # per port: [bucket start, mean receive, mean transmit, number of samples]
        self._ports: dict[int, deque[list[float]]] = {}

    def add(self, now: float, rates: dict[int, tuple[float | None, float | None]]) -> None:
        """Add the rates of one poll. A poll without both rates (a counter reset) adds nothing."""
        bucket = int(now // BUCKET * BUCKET)
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
        self._prune(bucket)

    def _prune(self, bucket: int) -> None:
        for port, values in list(self._ports.items()):
            while values and values[0][0] <= bucket - KEEP:
                values.popleft()
            if not values:
                del self._ports[port]

    def series(self, port: int) -> list[tuple[float, float, float]]:
        """(bucket start, receive, transmit) for a port, oldest first."""
        return [(t, rx, tx) for t, rx, tx, _ in self._ports.get(port, ())]

    def as_dict(self) -> dict[str, Any]:
        """What gets stored."""
        return {
            "ports": {
                str(port): [[t, round(rx, 3), round(tx, 3), n] for t, rx, tx, n in values]
                for port, values in self._ports.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Any, now: float) -> RateHistory:
        """Restore what was stored; anything that does not look right is left out."""
        history = cls()
        ports = data.get("ports") if isinstance(data, dict) else None
        if not isinstance(ports, dict):
            return history
        for key, rows in ports.items():
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
                history._ports[int(key)] = values
        history._prune(int(now // BUCKET * BUCKET))
        return history
