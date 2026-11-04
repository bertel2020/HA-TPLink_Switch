"""Tests for the SNMP client, with pysnmp's request functions replaced."""

from unittest.mock import AsyncMock, MagicMock, patch

from pysnmp.proto.rfc1902 import Counter64, Integer32, OctetString
from pysnmp.proto.rfc1905 import NoSuchInstance
import pytest

from custom_components.tplink_switch_snmp import snmp as module
from custom_components.tplink_switch_snmp.snmp import SnmpClient, SnmpError

OID = "1.3.6.1.2.1.1.5.0"


def _client() -> SnmpClient:
    client = SnmpClient(
        MagicMock(), "192.168.79.15", 161, {"version": "2c", "community": "homeassistant"}
    )
    client._target = MagicMock()  # skip the real transport
    return client


def _walk(*rounds):
    """An async generator in place of bulk_walk_cmd, answering with the given rounds."""

    async def generator(*_args, **_kwargs):
        for round_ in rounds:
            yield round_

    return generator


async def test_get_converts_values() -> None:
    binds = [
        (OID, OctetString(b"TL-SG3424")),
        ("1.3.6.1.2.1.1.3.0", Integer32(42)),
        ("1.3.6.1.2.1.31.1.1.1.6.1", Counter64(2**40)),
    ]
    with patch.object(module, "get_cmd", AsyncMock(return_value=(None, 0, 0, binds))):
        result = await _client().get(OID)

    assert result == {OID: b"TL-SG3424", "1.3.6.1.2.1.1.3.0": 42, "1.3.6.1.2.1.31.1.1.1.6.1": 2**40}


async def test_get_leaves_out_what_the_switch_does_not_know() -> None:
    binds = [(OID, NoSuchInstance())]
    with patch.object(module, "get_cmd", AsyncMock(return_value=(None, 0, 0, binds))):
        assert await _client().get(OID) == {}


async def test_get_reports_a_timeout() -> None:
    with (
        patch.object(module, "get_cmd", AsyncMock(return_value=("No SNMP response", 0, 0, []))),
        pytest.raises(SnmpError, match="No SNMP response"),
    ):
        await _client().get(OID)


async def test_get_reports_an_error_status() -> None:
    status = MagicMock()
    status.prettyPrint.return_value = "noAccess"
    with (
        patch.object(module, "get_cmd", AsyncMock(return_value=(None, status, 1, []))),
        pytest.raises(SnmpError, match="noAccess"),
    ):
        await _client().get(OID)


async def test_walk_returns_index_suffixes() -> None:
    prefix = "1.3.6.1.2.1.2.2.1.8"
    rounds = [
        (None, 0, 0, [(f"{prefix}.1", Integer32(1)), (f"{prefix}.2", Integer32(2))]),
        (None, 0, 0, [(f"{prefix}.3", Integer32(1))]),
    ]
    with patch.object(module, "bulk_walk_cmd", _walk(*rounds)):
        assert await _client().walk(prefix) == {"1": 1, "2": 2, "3": 1}


async def test_walk_ignores_rows_outside_the_column() -> None:
    prefix = "1.3.6.1.2.1.2.2.1.8"
    rounds = [
        (None, 0, 0, [(f"{prefix}.1", Integer32(1)), ("1.3.6.1.2.1.2.2.1.9.1", Integer32(7))])
    ]
    with patch.object(module, "bulk_walk_cmd", _walk(*rounds)):
        assert await _client().walk(prefix) == {"1": 1}


async def test_walk_reports_an_error() -> None:
    with (
        patch.object(module, "bulk_walk_cmd", _walk(("No SNMP response", 0, 0, []))),
        pytest.raises(SnmpError),
    ):
        await _client().walk("1.3.6.1.2.1.2.2.1.8")


async def test_walk_many_keeps_the_names() -> None:
    client = _client()
    client.walk = AsyncMock(side_effect=[{"1": 1}, {"1": 2}])

    assert await client.walk_many({"a": "1.1", "b": "1.2"}) == {"a": {"1": 1}, "b": {"1": 2}}


def test_community_versions():
    v1 = module.build_auth({"version": "1", "community": "c"})
    v2c = module.build_auth({"version": "2c", "community": "c"})
    assert (v1.message_processing_model, v2c.message_processing_model) == (0, 1)
    assert (
        module.build_auth({"community": "c"}).message_processing_model == 1
    )  # entries from before v3 have no version


def test_v3_user_levels():
    base = {"version": "3", "username": "ha"}
    none = module.build_auth(base)
    auth = module.build_auth({**base, "auth_protocol": "sha256", "auth_key": "authpassword"})
    priv = module.build_auth(
        {
            **base,
            "auth_protocol": "sha",
            "auth_key": "authpassword",
            "priv_protocol": "aes256",
            "priv_key": "privpassword",
        }
    )
    assert none.userName == "ha" and none.authentication_key is None
    assert auth.authentication_protocol == module.AUTH["sha256"] and auth.privacy_key is None
    assert priv.privacy_protocol == module.PRIV["aes256"] and priv.privacy_key is not None


def test_v3_encryption_without_authentication_is_ignored():
    user = module.build_auth(
        {
            "version": "3",
            "username": "ha",
            "auth_protocol": "none",
            "priv_protocol": "aes128",
            "priv_key": "privpassword",
        }
    )
    assert user.privacy_key is None


async def test_v1_walks_with_getnext() -> None:
    prefix = "1.3.6.1.2.1.2.2.1.8"
    client = SnmpClient(MagicMock(), "h", 161, {"version": "1", "community": "c"})
    client._target = MagicMock()
    rounds = [(None, 0, 0, [(f"{prefix}.1", Integer32(1))])]
    with (
        patch.object(module, "walk_cmd", _walk(*rounds)) as walk,
        patch.object(module, "bulk_walk_cmd", side_effect=AssertionError("v1 has no GETBULK")),
    ):
        assert await client.walk(prefix) == {"1": 1}
    assert walk is not None
