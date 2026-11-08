"""Tests for the integration's own rate history and how it is kept."""

import time

from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tplink_switch_snmp.const import DOMAIN
from custom_components.tplink_switch_snmp.history import (
    BUCKET,
    COUNT_ACTIVE,
    COUNT_MACS,
    KEEP,
    RANGES,
    LinkLog,
    RateHistory,
)

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

    stored = history.as_dict()
    assert (stored["ports"], stored["hourly"], stored["two_hourly"]) == ({}, {}, {})


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
        stored = RateHistory.from_dict(garbage, NOW).as_dict()
        assert (stored["ports"], stored["hourly"], stored["two_hourly"]) == ({}, {}, {})


# ---- the hourly values for a week


def test_hours_average_everything_in_them() -> None:
    history = RateHistory()
    hour = NOW // 3600 * 3600
    history.add(hour + 10, {1: (10.0, 1.0)})
    history.add(hour + 400, {1: (30.0, 3.0)})  # another five-minute bucket, the same hour
    history.add(hour + 3000, {1: (20.0, 2.0)})

    assert history.series(1, "7d") == [(hour, 20.0, 2.0)]
    assert len(history.series(1, "24h")) == 3  # the five-minute values stay


def test_hours_are_kept_for_a_week_and_five_minutes_for_a_day() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 1.0)})
    history.add(NOW + 2 * KEEP, {1: (20.0, 2.0)})  # two days later

    assert len(history.series(1, "24h")) == 1  # the first value is a day old
    assert len(history.series(1, "7d")) == 2  # but it is still within the week


def test_the_week_forgets_after_seven_days() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 1.0)})
    history.add(NOW + RANGES["7d"][1] + 3600, {1: (20.0, 2.0)})

    assert len(history.series(1, "7d")) == 1


def test_a_file_from_before_the_week_still_loads() -> None:
    old = {"ports": {"1": [[START, 5, 5, 1]]}}  # no "hourly" in it
    restored = RateHistory.from_dict(old, NOW)

    assert restored.series(1) == [(START, 5.0, 5.0)]
    assert restored.series(1, "7d") == []


def test_both_tiers_survive_a_round_trip() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 2.0)})
    restored = RateHistory.from_dict(history.as_dict(), NOW + 30)

    assert restored.series(1) == history.series(1)
    assert restored.series(1, "7d") == history.series(1, "7d")


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


def test_total_series_sums_ports_and_survives_storage() -> None:
    history = RateHistory()
    history.add(NOW, {1: (10.0, 2.0), 2: (5.0, 1.0)})
    assert history.total_series("30d") == [(NOW // 7200 * 7200, 15.0, 3.0)]
    restored = RateHistory.from_dict(history.as_dict(), NOW)
    assert restored.total_series("30d") == history.total_series("30d")
    assert RateHistory().total_series("7d") == []


def test_counts_are_averaged_and_survive_storage() -> None:
    history = RateHistory()
    history.add_counts(NOW, 10, 40)
    history.add_counts(NOW + 30, 12, 50)
    assert history.count_series(COUNT_ACTIVE, "24h") == [(START, 11.0)]
    assert history.count_series(COUNT_MACS, "24h") == [(START, 45.0)]
    restored = RateHistory.from_dict(history.as_dict(), NOW)
    assert restored.count_series(COUNT_MACS, "30d") == history.count_series(COUNT_MACS, "30d")


def test_link_log_records_changes_with_speed_and_counts_the_last_day() -> None:
    log = LinkLog(NOW - 5 * 86400)
    log.add(NOW - 2 * 86400, 3, True, 1000)
    log.add(NOW - 100, 3, False, 0)
    log.add(NOW - 50, 3, True, 100, flap=True)  # down and up again between two polls
    assert log.count(NOW, 3) == 3  # the one two days ago is older than 24 hours
    assert log.count(NOW, 4) == 0
    assert [e[1:] for e in log.events(NOW, 3, 86400)] == [[0, 0], [0, 0], [1, 100]]
    assert len(log.events(NOW, 3)) == 4


def test_link_log_survives_storage_and_ignores_bad_rows() -> None:
    log = LinkLog(NOW - 86400)
    log.add(NOW - 60, 1, False, 0)
    restored = LinkLog.from_dict(log.as_dict(), NOW)
    assert restored.since == NOW - 86400
    assert restored.events(NOW, 1) == [[NOW - 60, 0, 0]]
    broken = {"since": "x", "ports": {"1": [[NOW - 60, 2, 0], ["a"], [NOW - 40, 1, 1000]], "b": []}}
    odd = LinkLog.from_dict(broken, NOW)
    assert odd.since == NOW
    assert odd.events(NOW, 1) == [[NOW - 40, 1, 1000]]
    assert LinkLog.from_dict(None, NOW).events(NOW, 1) == []
