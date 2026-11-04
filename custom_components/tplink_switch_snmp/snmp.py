"""Small asynchronous SNMP client for the switch."""

from __future__ import annotations

import asyncio
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    bulk_walk_cmd,
    get_cmd,
)

_MISSING = {"NoSuchObject", "NoSuchInstance", "EndOfMibView"}


class SnmpError(Exception):
    """The switch did not answer or refused the request."""


def _py(value: Any) -> Any:
    """Turn a pysnmp value into an int, bytes or str."""
    if hasattr(value, "asOctets"):
        return bytes(value.asOctets())
    try:
        return int(value)
    except (TypeError, ValueError):
        return value.prettyPrint()


class SnmpClient:
    """Read-only SNMP v2c access to one switch."""

    def __init__(
        self,
        engine: SnmpEngine,
        host: str,
        port: int,
        community: str,
        timeout: int = 3,
        retries: int = 1,
    ) -> None:
        self._engine = engine
        self._host = host
        self._port = port
        self._timeout = timeout
        self._retries = retries
        # mpModel 1 is SNMP v2c.
        self._auth = CommunityData(community, mpModel=1)
        self._context = ContextData()
        self._target: UdpTransportTarget | None = None

    def close(self) -> None:
        """Release the SNMP engine."""
        self._engine.close_dispatcher()

    async def _get_target(self) -> UdpTransportTarget:
        if self._target is None:
            try:
                self._target = await UdpTransportTarget.create(
                    (self._host, self._port),
                    timeout=self._timeout,
                    retries=self._retries,
                )
            except Exception as err:  # noqa: BLE001 - name resolution and sockets
                raise SnmpError(f"cannot reach {self._host}: {err}") from err
        return self._target

    async def get(self, *oids: str) -> dict[str, Any]:
        """Read single values; an OID the switch does not know is left out."""
        target = await self._get_target()
        error, status, index, binds = await get_cmd(
            self._engine,
            self._auth,
            target,
            self._context,
            *(ObjectType(ObjectIdentity(oid)) for oid in oids),
        )
        if error:
            raise SnmpError(str(error))
        if status:
            raise SnmpError(f"{status.prettyPrint()} at {index}")
        return {
            str(name): _py(value)
            for name, value in binds
            if type(value).__name__ not in _MISSING
        }

    async def walk(self, oid: str) -> dict[str, Any]:
        """Walk one column and return {index suffix: value}."""
        target = await self._get_target()
        prefix = oid + "."
        result: dict[str, Any] = {}
        async for error, status, index, binds in bulk_walk_cmd(
            self._engine,
            self._auth,
            target,
            self._context,
            0,
            25,
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
        ):
            if error:
                raise SnmpError(str(error))
            if status:
                raise SnmpError(f"{status.prettyPrint()} at {index}")
            for name, value in binds:
                name = str(name)
                if name.startswith(prefix) and type(value).__name__ not in _MISSING:
                    result[name[len(prefix) :]] = _py(value)
        return result

    async def walk_many(self, oids: dict[str, str]) -> dict[str, dict[str, Any]]:
        """Walk several columns at once, keyed by the given names."""
        columns = await asyncio.gather(*(self.walk(oid) for oid in oids.values()))
        return dict(zip(oids, columns, strict=True))
