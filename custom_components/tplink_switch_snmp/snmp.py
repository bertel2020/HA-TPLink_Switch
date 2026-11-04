"""Small asynchronous SNMP client for the switch."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    bulk_walk_cmd,
    get_cmd,
    usmAesCfb128Protocol,
    usmAesCfb192Protocol,
    usmAesCfb256Protocol,
    usmDESPrivProtocol,
    usmHMAC128SHA224AuthProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMAC256SHA384AuthProtocol,
    usmHMAC384SHA512AuthProtocol,
    usmHMACMD5AuthProtocol,
    usmHMACSHAAuthProtocol,
    walk_cmd,
)

from .const import (
    CONF_AUTH_KEY,
    CONF_AUTH_PROTOCOL,
    CONF_COMMUNITY,
    CONF_PRIV_KEY,
    CONF_PRIV_PROTOCOL,
    CONF_USERNAME,
    CONF_VERSION,
    DEFAULT_VERSION,
    NO_PROTOCOL,
    VERSION_1,
    VERSION_3,
)

AUTH = {
    "md5": usmHMACMD5AuthProtocol,
    "sha": usmHMACSHAAuthProtocol,
    "sha224": usmHMAC128SHA224AuthProtocol,
    "sha256": usmHMAC192SHA256AuthProtocol,
    "sha384": usmHMAC256SHA384AuthProtocol,
    "sha512": usmHMAC384SHA512AuthProtocol,
}
PRIV = {
    "des": usmDESPrivProtocol,
    "aes128": usmAesCfb128Protocol,
    "aes192": usmAesCfb192Protocol,
    "aes256": usmAesCfb256Protocol,
}

_MISSING = {"NoSuchObject", "NoSuchInstance", "EndOfMibView"}


class SnmpError(Exception):
    """The switch did not answer or refused the request."""


def build_auth(config: Mapping[str, Any]) -> CommunityData | UsmUserData:
    """The SNMP credentials of a config entry: a community or a v3 user."""
    version = config.get(CONF_VERSION, DEFAULT_VERSION)
    if version != VERSION_3:
        # mpModel 0 is SNMP v1, 1 is v2c
        return CommunityData(config[CONF_COMMUNITY], mpModel=0 if version == VERSION_1 else 1)

    kwargs: dict[str, Any] = {}
    auth = config.get(CONF_AUTH_PROTOCOL, NO_PROTOCOL)
    if auth != NO_PROTOCOL:
        kwargs["authKey"] = config[CONF_AUTH_KEY]
        kwargs["authProtocol"] = AUTH[auth]
        priv = config.get(CONF_PRIV_PROTOCOL, NO_PROTOCOL)
        if priv != NO_PROTOCOL:
            kwargs["privKey"] = config[CONF_PRIV_KEY]
            kwargs["privProtocol"] = PRIV[priv]
    return UsmUserData(config[CONF_USERNAME], **kwargs)


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
        config: Mapping[str, Any],
        timeout: int = 3,
        retries: int = 1,
    ) -> None:
        self._engine = engine
        self._host = host
        self._port = port
        self._timeout = timeout
        self._retries = retries
        self._auth = build_auth(config)
        # SNMPv1 has no GETBULK, so it walks with GETNEXT.
        self._v1 = config.get(CONF_VERSION, DEFAULT_VERSION) == VERSION_1
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
            str(name): _py(value) for name, value in binds if type(value).__name__ not in _MISSING
        }

    async def walk(self, oid: str) -> dict[str, Any]:
        """Walk one column and return {index suffix: value}."""
        target = await self._get_target()
        prefix = oid + "."
        result: dict[str, Any] = {}
        request = ObjectType(ObjectIdentity(oid))
        if self._v1:
            walk = walk_cmd(
                self._engine, self._auth, target, self._context, request, lexicographicMode=False
            )
        else:
            walk = bulk_walk_cmd(
                self._engine,
                self._auth,
                target,
                self._context,
                0,
                25,
                request,
                lexicographicMode=False,
            )
        async for error, status, index, binds in walk:
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
