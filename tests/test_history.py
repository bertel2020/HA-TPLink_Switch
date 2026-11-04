"""Tests for the integration's own rate history and how it is kept."""

import time

from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp.const import DOMAIN
from custom_components.tplink_switch_snmp.history import BUCKET, KEEP, RateHistory

NOW = 1_800_000_000.0  # any time; the buckets are computed from it
START = NOW // BUCKET * BUCKET


def test_samples_in_one_bucket_are_averaged() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 2.0)})
    history.add(NOW + 30, {1: (20.0, 4.0)})
    history.add(NOW + 60, {1: (60.0, 12.0)})

    assert history.series(1) == [(START, 30.0, 6.0)]


def test_a_new_bucket_starts_after_five_minutes() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 1.0)})
    history.add(NOW + BUCKET, {1: (50.0, 5.0)})

    assert history.series(1) == [(START, 10.0, 1.0), (START + BUCKET, 50.0, 5.0)]


def test_old_values_are_dropped_after_a_day() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 1.0)})
    history.add(NOW + KEEP, {1: (20.0, 2.0)})

    assert [t for t, _, _ in history.series(1)] == [START + KEEP]


def test_a_port_that_goes_quiet_disappears_with_its_values() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 1.0), 2: (5.0, 5.0)})
    history.add(NOW + KEEP, {1: (20.0, 2.0)})

    assert history.series(2) == []


def test_a_poll_without_both_rates_adds_nothing() -> None:
    history = RateHistory()
    history.add(NOW, {1: (None, None), 2: (5.0, None), 3: (None, 5.0)})

    assert history.as_dict() == {"ports": {}}


def test_the_clock_going_back_keeps_what_is_there() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 1.0)})
    history.add(NOW - 2 * BUCKET, {1: (99.0, 9.0)})

    assert history.series(1) == [(START, 10.0, 1.0)]


def test_unknown_ports_have_no_series() -> None:
    assert RateHistory().series(7) == []


def test_it_survives_a_round_trip_and_keeps_averaging() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 2.0)})
    history.add(NOW + 30, {1: (30.0, 6.0)})

    restored = RateHistory.from_dict(history.as_dict(), NOW + 60)
    assert restored.series(1) == [(START, 20.0, 4.0)]
    restored.add(NOW + 60, {1: (50.0, 10.0)})  # the third sample of the same bucket
    assert restored.series(1) == [(START, 30.0, 6.0)]


def test_restoring_drops_what_is_too_old_or_broken() -> None:
    data = {
        "ports": {
            "1": [[START - 2 * KEEP, 1, 1, 1], [START, 5, 5, 1]],
            "2": [["x", 1, 1, 1], [START, 1, 1, 0], [START, 2, 2]],
            "x": [[START, 1, 1, 1]],
            "3": "not a list",
        }
    }
    restored = RateHistory.from_dict(data, NOW)

    assert restored.series(1) == [(START, 5.0, 5.0)]
    assert restored.as_dict()["ports"].keys() == {"1"}


def test_restoring_garbage_gives_an_empty_history() -> None:
    for garbage in (None, [], "text", {"ports": 5}):
        assert RateHistory.from_dict(garbage, NOW).as_dict() == {"ports": {}}


# ---- in the integration ------------------------------------------------------------------


def _key(entry: MockConfigEntry) -> str:
    return f"{DOMAIN}.{entry.entry_id}.history"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_rates_are_collected_with_every_poll(
    hass: HomeAssistant, snmp, entry, tables
) -> None:
    await _setup(hass, entry)
    assert entry.runtime_data.history.series(1) == []  # the first poll has no rate yet

    tables["rx"]["1"] += 125_000_000
    await entry.runtime_data.async_refresh()

    series = entry.runtime_data.history.series(1)
    assert len(series) == 1 and series[0][1] > 0
    assert entry.runtime_data.history.series(2) == []  # no link, nothing to draw


async def test_the_history_is_saved_when_home_assistant_stops(
    hass: HomeAssistant, snmp, entry, tables, hass_storage
) -> None:
    await _setup(hass, entry)
    tables["rx"]["1"] += 125_000_000
    await entry.runtime_data.async_refresh()
    assert _key(entry) not in hass_storage  # not written at once

    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)  # what Home Assistant does at shutdown
    await hass.async_block_till_done()

    assert "1" in hass_storage[_key(entry)]["data"]["ports"]


async def test_the_stored_history_is_restored_at_start(
    hass: HomeAssistant, snmp, entry, hass_storage
) -> None:
    now = time.time()
    bucket = now // BUCKET * BUCKET - BUCKET
    hass_storage[_key(entry)] = {
        "version": 1,
        "key": _key(entry),
        "data": {"ports": {"1": [[bucket, 12.5, 3.5, 4]]}},
    }

    await _setup(hass, entry)

    assert entry.runtime_data.history.series(1) == [(bucket, 12.5, 3.5)]


async def test_the_history_is_removed_with_the_switch(
    hass: HomeAssistant, snmp, entry, tables, hass_storage
) -> None:
    await _setup(hass, entry)
    tables["rx"]["1"] += 125_000_000
    await entry.runtime_data.async_refresh()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)  # what Home Assistant does at shutdown
    await hass.async_block_till_done()
    assert _key(entry) in hass_storage

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert _key(entry) not in hass_storage
