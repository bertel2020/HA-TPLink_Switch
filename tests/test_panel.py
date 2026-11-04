"""Tests for serving the panel and the dashboard card."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.tplink_switch_snmp import panel
from custom_components.tplink_switch_snmp.const import DOMAIN, PANEL_PATH


def _frontend(hass: HomeAssistant) -> MagicMock:
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.config.components.add("frontend")
    return hass.http


async def test_nothing_is_registered_without_the_frontend(hass: HomeAssistant) -> None:
    with patch.object(panel.panel_custom, "async_register_panel", AsyncMock()) as register:
        await panel.async_register_panel(hass)
    register.assert_not_awaited()


async def test_files_card_and_panel_are_registered(hass: HomeAssistant) -> None:
    http = _frontend(hass)
    with (
        patch.object(panel.frontend, "add_extra_js_url") as add_js,
        patch.object(panel.panel_custom, "async_register_panel", AsyncMock()) as register,
    ):
        await panel.async_register_panel(hass)

    http.async_register_static_paths.assert_awaited_once()
    assert add_js.call_args.args[1].startswith(
        "/tplink_switch_snmp_static/tplink-switch-card.js?v="
    )
    kwargs = register.await_args.kwargs
    assert kwargs["frontend_url_path"] == PANEL_PATH and kwargs["require_admin"] is True
    assert kwargs["module_url"].startswith("/tplink_switch_snmp_static/switch-panel.js?v=")


async def test_a_switch_set_up_again_does_not_register_the_files_twice(
    hass: HomeAssistant,
) -> None:
    """The panel goes with the last switch; the static path and the card cannot be removed."""
    http = _frontend(hass)
    with (
        patch.object(panel.frontend, "add_extra_js_url") as add_js,
        patch.object(panel.panel_custom, "async_register_panel", AsyncMock()) as register,
    ):
        await panel.async_register_panel(hass)
        await panel.async_register_panel(hass)  # e.g. after the last switch was removed and added

    assert http.async_register_static_paths.await_count == 1
    assert add_js.call_count == 1
    assert register.await_count == 2  # the panel itself is registered again
    assert DOMAIN in hass.data


def test_the_card_file_is_part_of_the_version() -> None:
    assert panel.CARD_FILE.is_file()
    assert panel.CARD_FILE.parent == panel.PANEL_FILE.parent  # so a change gives a new URL
