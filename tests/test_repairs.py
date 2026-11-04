"""Tests for the repair issue that tells a switch has been silent for a while."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp.const import DOMAIN
from custom_components.tplink_switch_snmp.coordinator import UNREACHABLE_AFTER
from custom_components.tplink_switch_snmp.snmp import SnmpError


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _issue(hass: HomeAssistant, entry: MockConfigEntry):
    return ir.async_get(hass).async_get_issue(DOMAIN, f"unreachable_{entry.entry_id}")


async def test_a_short_outage_raises_nothing(hass: HomeAssistant, snmp, entry, freezer) -> None:
    await _setup(hass, entry)
    snmp.walk_many.side_effect = SnmpError("timeout")

    await entry.runtime_data.async_refresh()
    freezer.tick(timedelta(seconds=UNREACHABLE_AFTER - 60))
    await entry.runtime_data.async_refresh()

    assert _issue(hass, entry) is None


async def test_a_long_outage_raises_an_issue(hass: HomeAssistant, snmp, entry, freezer) -> None:
    await _setup(hass, entry)
    snmp.walk_many.side_effect = SnmpError("timeout")

    await entry.runtime_data.async_refresh()
    freezer.tick(timedelta(seconds=UNREACHABLE_AFTER + 1))
    await entry.runtime_data.async_refresh()

    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.translation_key == "unreachable"
    assert issue.translation_placeholders == {"name": "TL-SG3424", "host": "192.168.79.15"}
    assert issue.is_fixable is False
    assert issue.severity is ir.IssueSeverity.WARNING


async def test_the_issue_goes_when_the_switch_answers(
    hass: HomeAssistant, snmp, entry, tables, freezer
) -> None:
    await _setup(hass, entry)
    good = snmp.walk_many.side_effect
    snmp.walk_many.side_effect = SnmpError("timeout")
    await entry.runtime_data.async_refresh()
    freezer.tick(timedelta(seconds=UNREACHABLE_AFTER + 1))
    await entry.runtime_data.async_refresh()
    assert _issue(hass, entry) is not None

    snmp.walk_many.side_effect = good
    await entry.runtime_data.async_refresh()

    assert _issue(hass, entry) is None


async def test_the_clock_starts_again_after_an_answer(
    hass: HomeAssistant, snmp, entry, freezer
) -> None:
    await _setup(hass, entry)
    good = snmp.walk_many.side_effect
    snmp.walk_many.side_effect = SnmpError("timeout")
    await entry.runtime_data.async_refresh()
    freezer.tick(timedelta(seconds=UNREACHABLE_AFTER - 10))
    snmp.walk_many.side_effect = good
    await entry.runtime_data.async_refresh()  # answered in time

    snmp.walk_many.side_effect = SnmpError("timeout")
    freezer.tick(timedelta(seconds=60))
    await entry.runtime_data.async_refresh()  # a new outage, one minute old

    assert _issue(hass, entry) is None


async def test_the_issue_is_removed_with_the_switch(
    hass: HomeAssistant, snmp, entry, freezer
) -> None:
    await _setup(hass, entry)
    snmp.walk_many.side_effect = SnmpError("timeout")
    await entry.runtime_data.async_refresh()
    freezer.tick(timedelta(seconds=UNREACHABLE_AFTER + 1))
    await entry.runtime_data.async_refresh()
    assert _issue(hass, entry) is not None

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert _issue(hass, entry) is None


def test_the_issue_has_a_text_in_both_languages() -> None:
    import json
    from pathlib import Path

    base = Path(__file__).parents[1] / "custom_components/tplink_switch_snmp"
    for path in ("strings.json", "translations/de.json", "translations/en.json"):
        issue = json.loads((base / path).read_text())["issues"]["unreachable"]
        assert "{name}" in issue["title"] and "{host}" in issue["description"]
