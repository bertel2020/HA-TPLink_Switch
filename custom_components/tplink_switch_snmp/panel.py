"""Sidebar panel "Switch": ports, traffic and devices at a glance (admins only).

A plain web component (frontend/switch-panel.js, no build step) served from the
integration; it reads the websocket API in websocket_api.py. Its parts (styles.js,
texts.js, theme.js, csv.js) are loaded with the same query string. That string carries a hash of all
panel files, so browsers load a new version of every part after an update.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_PATH

STATIC_URL = f"/{DOMAIN}_static"
PANEL_FILE = Path(__file__).parent / "frontend" / "switch-panel.js"
CARD_FILE = PANEL_FILE.parent / "tplink-switch-card.js"
DATA_VERSION = "frontend_version"


def _version() -> str:
    """Hash of all panel files: a change in any part gives a new URL."""
    digest = hashlib.sha256()
    for path in sorted(PANEL_FILE.parent.glob("*.js")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the files and load the card once, and register the panel if it is not there.

    Skipped without the frontend (e.g. in tests).
    """
    if hass.http is None or "frontend" not in hass.config.components:
        return
    domain_data = hass.data.setdefault(DOMAIN, {})
    # The static path and the card can be registered only once; the panel comes and goes
    # with the last switch, so a switch that is set up again must not do it a second time.
    if DATA_VERSION not in domain_data:
        version = await hass.async_add_executor_job(_version)
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(PANEL_FILE.parent), cache_headers=False)]
        )
        frontend.add_extra_js_url(hass, f"{STATIC_URL}/{CARD_FILE.name}?v={version}")
        domain_data[DATA_VERSION] = version
    if PANEL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="tplink-switch-panel",
        sidebar_title="Switch",
        sidebar_icon="mdi:lan",
        module_url=f"{STATIC_URL}/switch-panel.js?v={domain_data[DATA_VERSION]}",
        require_admin=True,
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    """Take the panel out again when the last switch is gone."""
    if PANEL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_PATH)
