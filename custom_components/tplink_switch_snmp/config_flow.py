"""Config flow for the TP-Link switch (SNMP)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import probatio
from pysnmp.hlapi.v3arch.asyncio import SnmpEngine

from .const import (
    AUTH_PROTOCOLS,
    CONF_ALLOW_WRITE,
    CONF_AUTH_KEY,
    CONF_AUTH_PROTOCOL,
    CONF_COMMUNITY,
    CONF_ENTITY_GROUPS,
    CONF_ENTITY_PORTS,
    CONF_PRIV_KEY,
    CONF_PRIV_PROTOCOL,
    CONF_PROTECTED_PORTS,
    CONF_SCAN_INTERVAL,
    CONF_TRAP_PORT,
    CONF_USERNAME,
    CONF_VERSION,
    CONF_WRITE_COMMUNITY,
    DEFAULT_COMMUNITY,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERSION,
    DOMAIN,
    ENTITY_GROUPS,
    MAX_SCAN_INTERVAL,
    MIN_KEY_LENGTH,
    MIN_SCAN_INTERVAL,
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


SCHEMA_CONNECTION = probatio.Schema(
    {
        probatio.Required(CONF_HOST): str,
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): int,
        probatio.Required(CONF_VERSION, default=DEFAULT_VERSION): _select(VERSIONS, "version"),
    }
)
SCHEMA_COMMUNITY = probatio.Schema(
    {probatio.Required(CONF_COMMUNITY, default=DEFAULT_COMMUNITY): str}
)
SCHEMA_USER = probatio.Schema(
    {
        probatio.Required(CONF_USERNAME): str,
        probatio.Required(CONF_AUTH_PROTOCOL, default="sha"): _select(
            [NO_PROTOCOL, *AUTH_PROTOCOLS], "auth_protocol"
        ),
        probatio.Optional(CONF_AUTH_KEY): _password(),
        probatio.Required(CONF_PRIV_PROTOCOL, default="aes128"): _select(
            [NO_PROTOCOL, *PRIV_PROTOCOLS], "priv_protocol"
        ),
        probatio.Optional(CONF_PRIV_KEY): _password(),
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SwitchOptionsFlow:
        return SwitchOptionsFlow()


class SwitchOptionsFlow(OptionsFlow):
    """How often the switch is asked, and whether it may send traps."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            # The options also hold the port names, which are not part of this form.
            options = {**self.config_entry.options, **user_input}
            options[CONF_SCAN_INTERVAL] = int(options[CONF_SCAN_INTERVAL])
            if CONF_PROTECTED_PORTS in options:
                options[CONF_PROTECTED_PORTS] = sorted(
                    int(n) for n in options[CONF_PROTECTED_PORTS]
                )
            if CONF_ENTITY_PORTS in options:
                options[CONF_ENTITY_PORTS] = sorted(int(n) for n in options[CONF_ENTITY_PORTS])
            if CONF_TRAP_PORT in options:
                options[CONF_TRAP_PORT] = int(options[CONF_TRAP_PORT])
            return self.async_create_entry(data=options)

        fields: dict[Any, Any] = {
            probatio.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            )
        }
        # Which entities to create: groups of them, and the ports they are made for.
        fields[probatio.Required(CONF_ENTITY_GROUPS, default=list(ENTITY_GROUPS))] = SelectSelector(
            SelectSelectorConfig(
                options=list(ENTITY_GROUPS),
                multiple=True,
                translation_key="entity_groups",
                mode=SelectSelectorMode.LIST,
            )
        )
        v3 = self.config_entry.data.get(CONF_VERSION, DEFAULT_VERSION) == VERSION_3
        # Traps need a community, which SNMPv3 does not have.
        if not v3:
            fields[probatio.Required(CONF_TRAP_PORT, default=0)] = NumberSelector(
                NumberSelectorConfig(min=0, max=65535, step=1, mode=NumberSelectorMode.BOX)
            )
        # Writing: off unless asked for. v1 and v2c write with a community of their own.
        fields[probatio.Required(CONF_ALLOW_WRITE, default=False)] = bool
        if not v3:
            fields[probatio.Optional(CONF_WRITE_COMMUNITY)] = TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            )
        coordinator = getattr(self.config_entry, "runtime_data", None)
        if coordinator is not None and coordinator.data:
            fields[probatio.Optional(CONF_ENTITY_PORTS, default=[])] = SelectSelector(
                SelectSelectorConfig(
                    options=[str(n) for n in sorted(coordinator.data.ports)],
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
            fields[probatio.Optional(CONF_PROTECTED_PORTS, default=[])] = SelectSelector(
                SelectSelectorConfig(
                    options=[str(n) for n in sorted(coordinator.data.ports)],
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                probatio.Schema(fields), self._suggested()
            ),
        )

    def _suggested(self) -> dict[str, Any]:
        """The saved options as the form shows them: the port numbers as text."""
        options = dict(self.config_entry.options)
        for key in (CONF_PROTECTED_PORTS, CONF_ENTITY_PORTS):
            if key in options:
                options[key] = [str(n) for n in options[key]]
        return options
