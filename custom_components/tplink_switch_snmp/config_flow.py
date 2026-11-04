"""Config flow for the TP-Link switch (SNMP)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from pysnmp.hlapi.v3arch.asyncio import SnmpEngine
import voluptuous as vol

from .const import (
    AUTH_PROTOCOLS,
    CONF_AUTH_KEY,
    CONF_AUTH_PROTOCOL,
    CONF_COMMUNITY,
    CONF_PRIV_KEY,
    CONF_PRIV_PROTOCOL,
    CONF_USERNAME,
    CONF_VERSION,
    DEFAULT_COMMUNITY,
    DEFAULT_PORT,
    DEFAULT_VERSION,
    DOMAIN,
    MIN_KEY_LENGTH,
    NO_PROTOCOL,
    OID_BRIDGE_ADDRESS,
    OID_SYS_NAME,
    PRIV_PROTOCOLS,
    VERSION_3,
    VERSIONS,
)
from .model import format_mac, text
from .snmp import SnmpClient, SnmpError


async def _probe(hass: HomeAssistant, data: Mapping[str, Any]) -> tuple[str, str]:
    """Ask the switch for its name and bridge MAC; raise SnmpError if it fails."""
    engine = await hass.async_add_executor_job(SnmpEngine)
    client = SnmpClient(engine, data[CONF_HOST], data[CONF_PORT], data, retries=0)
    try:
        values = await client.get(OID_SYS_NAME, OID_BRIDGE_ADDRESS)
    finally:
        client.close()
    name = values.get(OID_SYS_NAME)
    mac = values.get(OID_BRIDGE_ADDRESS)
    if not name or not isinstance(mac, bytes) or len(mac) != 6:
        raise SnmpError("not a bridge")
    return text(name), format_mac(mac)


def _select(options: tuple[str, ...] | list[str], key: str) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=list(options), translation_key=key, mode=SelectSelectorMode.DROPDOWN
        )
    )


def _password() -> TextSelector:
    return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


SCHEMA_CONNECTION = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_VERSION, default=DEFAULT_VERSION): _select(VERSIONS, "version"),
    }
)
SCHEMA_COMMUNITY = vol.Schema({vol.Required(CONF_COMMUNITY, default=DEFAULT_COMMUNITY): str})
SCHEMA_USER = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_AUTH_PROTOCOL, default="sha"): _select(
            [NO_PROTOCOL, *AUTH_PROTOCOLS], "auth_protocol"
        ),
        vol.Optional(CONF_AUTH_KEY): _password(),
        vol.Required(CONF_PRIV_PROTOCOL, default="aes128"): _select(
            [NO_PROTOCOL, *PRIV_PROTOCOLS], "priv_protocol"
        ),
        vol.Optional(CONF_PRIV_KEY): _password(),
    }
)


def check_user(data: Mapping[str, Any]) -> str | None:
    """The error key for SNMPv3 settings that cannot work, or None."""
    auth = data.get(CONF_AUTH_PROTOCOL, NO_PROTOCOL)
    priv = data.get(CONF_PRIV_PROTOCOL, NO_PROTOCOL)
    if priv != NO_PROTOCOL and auth == NO_PROTOCOL:
        return "privacy_needs_authentication"
    if auth != NO_PROTOCOL and len(data.get(CONF_AUTH_KEY) or "") < MIN_KEY_LENGTH:
        return "key_too_short"
    if priv != NO_PROTOCOL and len(data.get(CONF_PRIV_KEY) or "") < MIN_KEY_LENGTH:
        return "key_too_short"
    return None


class SwitchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the address and the SNMP credentials, and check that the switch answers."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection: dict[str, Any] = {}

    # ---- address and version -------------------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._connection = dict(user_input)
            return await self._credentials()
        return self.async_show_form(step_id="user", data_schema=SCHEMA_CONNECTION)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change address, version or credentials of a switch that is already set up."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            self._connection = dict(user_input)
            return await self._credentials()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(SCHEMA_CONNECTION, entry.data),
            description_placeholders={"title": entry.title},
        )

    async def _credentials(self) -> ConfigFlowResult:
        if self._connection[CONF_VERSION] == VERSION_3:
            return await self.async_step_auth()
        return await self.async_step_community()

    # ---- credentials ---------------------------------------------------------------------------

    async def async_step_community(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._finish({**self._connection, **user_input}, errors)
            if result:
                return result
        return self.async_show_form(
            step_id="community",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA_COMMUNITY, user_input or self._previous()
            ),
            errors=errors,
        )

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := check_user(user_input):
                errors["base"] = error
            else:
                result = await self._finish({**self._connection, **user_input}, errors)
                if result:
                    return result
        return self.async_show_form(
            step_id="auth",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA_USER, user_input or self._previous()
            ),
            errors=errors,
        )

    def _previous(self) -> Mapping[str, Any]:
        """Values to suggest: those of the entry that is being reconfigured."""
        if self.source == SOURCE_RECONFIGURE:
            return self._get_reconfigure_entry().data
        return {}

    async def _finish(
        self, data: dict[str, Any], errors: dict[str, str]
    ) -> ConfigFlowResult | None:
        """Check the switch and create or update the entry; None if it needs another try."""
        try:
            name, mac = await _probe(self.hass, data)
        except SnmpError:
            errors["base"] = "cannot_connect"
            return None

        await self.async_set_unique_id(mac)
        if self.source == SOURCE_RECONFIGURE:
            # The new address must answer with the same switch, not another one.
            self._abort_if_unique_id_mismatch(reason="wrong_device")
            entry = self._get_reconfigure_entry()
            # Credentials of the other SNMP version must not stay behind in the entry.
            return self.async_update_reload_and_abort(entry, data=data)

        self._abort_if_unique_id_configured(updates=data)
        return self.async_create_entry(title=name, data=data)
