"""Config flow for the TP-Link switch (SNMP)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from pysnmp.hlapi.v3arch.asyncio import SnmpEngine
import voluptuous as vol

from .const import (
    CONF_COMMUNITY,
    DEFAULT_COMMUNITY,
    DEFAULT_PORT,
    DOMAIN,
    OID_BRIDGE_ADDRESS,
    OID_SYS_NAME,
)
from .model import format_mac, text
from .snmp import SnmpClient, SnmpError


async def _probe(hass: HomeAssistant, data: dict[str, Any]) -> tuple[str, str]:
    """Ask the switch for its name and bridge MAC; raise SnmpError if it fails."""
    engine = await hass.async_add_executor_job(SnmpEngine)
    client = SnmpClient(engine, data[CONF_HOST], data[CONF_PORT], data[CONF_COMMUNITY], retries=0)
    try:
        values = await client.get(OID_SYS_NAME, OID_BRIDGE_ADDRESS)
    finally:
        client.close()
    name = values.get(OID_SYS_NAME)
    mac = values.get(OID_BRIDGE_ADDRESS)
    if not name or not isinstance(mac, bytes) or len(mac) != 6:
        raise SnmpError("not a bridge")
    return text(name), format_mac(mac)


class SwitchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for host and community and check that the switch answers."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                name, mac = await _probe(self.hass, user_input)
            except SnmpError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_COMMUNITY: user_input[CONF_COMMUNITY],
                    }
                )
                return self.async_create_entry(title=name, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_COMMUNITY, default=DEFAULT_COMMUNITY): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
