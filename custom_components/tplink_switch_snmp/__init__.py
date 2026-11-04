"""TP-Link switch (SNMP) integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from pysnmp.hlapi.v3arch.asyncio import SnmpEngine

from .const import CONF_COMMUNITY
from .coordinator import SwitchConfigEntry, SwitchCoordinator
from .snmp import SnmpClient

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SwitchConfigEntry) -> bool:
    """Set up one switch."""
    # Creating the engine loads MIB data from disk, so keep it off the event loop.
    engine = await hass.async_add_executor_job(SnmpEngine)
    client = SnmpClient(
        engine,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_COMMUNITY],
    )
    coordinator = SwitchCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        engine.close_dispatcher()
        raise
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SwitchConfigEntry) -> bool:
    """Unload a switch."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.client.close()
    return unloaded
