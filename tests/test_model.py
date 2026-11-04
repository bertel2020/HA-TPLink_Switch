"""Tests for the pure data model (loaded by path, no Home Assistant needed)."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_PATH = Path(__file__).parents[1] / "custom_components/tplink_switch_snmp/model.py"
_spec = spec_from_file_location("switch_model", _PATH)
model = module_from_spec(_spec)
sys.modules["switch_model"] = model
_spec.loader.exec_module(model)


def _tables():
    return {
        "name": {
            "1": b"port 1: Gigabit Copper",
            "2": b"port 2: Gigabit Copper",
            "25": b"AUX",
        },
        "oper": {"1": 1, "2": 2, "25": 1},
        "speed": {"1": 1000, "2": 0},
        "rx": {"1": 1_000_000, "2": 0},
        "tx": {"1": 2_000_000, "2": 0},
        "rx_err": {"1": 0, "2": 0},
        "tx_err": {"1": 3, "2": 0},
    }


def test_only_physical_ports_are_kept():
    ports = model.build_ports(_tables(), {}, {})
    assert sorted(ports) == [1, 2]
    assert ports[1].up and ports[1].speed == 1000
    assert not ports[2].up and ports[2].speed == 0
    assert ports[1].tx_errors == 3


def test_macs_are_assigned_through_the_base_port_table():
    fdb = {"1.0.4.32.249.54.2": 1, "1.0.8.220.84.149.70": 1}
    ports = model.build_ports(_tables(), fdb, {"1": 1, "2": 2})
    assert ports[1].macs == ["00:04:20:f9:36:02", "00:08:dc:54:95:46"]
    assert ports[2].macs == []


def test_ports_are_the_bridge_ports_whatever_they_are_called():
    tables = _tables()
    tables["name"] = {
        "1": b"gigabitEthernet 1/0/1",
        "2": b"gigabitEthernet 1/0/2",
        "99": b"Vlan-interface1",
    }
    tables["oper"]["99"] = 1
    ports = model.build_ports(tables, {}, {"1": 1, "2": 2})
    assert sorted(ports) == [1, 2]  # the VLAN interface is not a bridge port
    assert ports[1].name == "gigabitEthernet 1/0/1"


def test_port_number_is_the_bridge_port_and_macs_follow_it():
    tables = _tables()
    tables["name"] = {"49157": b"1/0/7"}
    tables["oper"] = {"49157": 1}
    for key in ("speed", "rx", "tx", "rx_err", "tx_err"):
        tables[key] = {"49157": 1000 if key == "speed" else 0}
    ports = model.build_ports(tables, {"1.0.4.32.249.54.2": 7}, {"7": 49157})
    assert list(ports) == [7]
    assert ports[7].if_index == 49157
    assert ports[7].macs == ["00:04:20:f9:36:02"]


def test_port_without_interface_data_is_skipped():
    ports = model.build_ports(_tables(), {}, {"1": 1, "2": 2, "3": 3})
    assert sorted(ports) == [1, 2]


def test_rates_from_counter_difference():
    old = model.build_ports(_tables(), {}, {})
    new_tables = _tables()
    new_tables["rx"]["1"] += 12_500_000  # 100 Mbit in 1 s
    new = model.build_ports(new_tables, {}, {})
    model.add_rates(new, old, 1.0)
    assert new[1].rx_rate == 100.0
    assert new[1].tx_rate == 0.0


def test_counter_reset_gives_no_rate():
    old = model.build_ports(_tables(), {}, {})
    reset = _tables()
    reset["rx"]["1"] = 10
    new = model.build_ports(reset, {}, {})
    model.add_rates(new, old, 30.0)
    assert new[1].rx_rate is None


def test_text_and_mac_helpers():
    assert model.text(b"TL-SG3424") == "TL-SG3424"
    assert model.format_mac(b"df\xb3l(d") == "64:66:b3:6c:28:64"


def test_manufacturer_from_the_enterprise_number():
    assert model.manufacturer("1.3.6.1.4.1.11863.1.1.3") == "TP-Link"
    assert model.manufacturer(".1.3.6.1.4.1.11863.1.1.3") == "TP-Link"
    assert model.manufacturer("1.3.6.1.4.1.9.1.1") is None  # not a known maker
    assert model.manufacturer("") is None
    assert model.manufacturer("1.3.6.1.2.1.1.1") is None  # not an enterprise OID


def test_uptime_in_seconds():
    tracker = model.UptimeTracker()
    assert tracker.seconds(15_800_000 * 100) == 15_800_000
    assert tracker.seconds(15_800_000 * 100 + 3000) == 15_800_030


def test_uptime_carries_on_after_the_counter_wraps():
    tracker = model.UptimeTracker()
    near_limit = model.TICKS_WRAP - 1000  # ten seconds before the wrap
    before = tracker.seconds(near_limit)
    after = tracker.seconds(2000)  # 20 seconds later, the counter started again
    assert before == near_limit // 100
    assert after == (model.TICKS_WRAP + 2000) // 100
    assert after > before


def test_uptime_survives_several_wraps():
    tracker = model.UptimeTracker()
    for _ in range(3):
        tracker.seconds(model.TICKS_WRAP - 100)
        wrapped = tracker.seconds(100)
    assert wrapped == (3 * model.TICKS_WRAP + 100) // 100


def test_uptime_starts_over_after_a_reboot():
    tracker = model.UptimeTracker()
    tracker.seconds(158 * 86400 * 100)
    assert tracker.seconds(6000) == 60  # fell from far below the limit: not a wrap


def test_reboot_after_a_wrap_resets_the_count():
    tracker = model.UptimeTracker()
    tracker.seconds(model.TICKS_WRAP - 100)
    tracker.seconds(100)  # wrapped once
    tracker.seconds(10_000_000)
    assert tracker.seconds(300) == 3  # rebooted


def test_32_bit_counter_wrap_still_gives_a_rate():
    old = model.build_ports(_tables(), {}, {})
    tables = _tables()
    tables["rx"]["1"] = 1_000  # wrapped: it was 2**32 - 124_999_000 before
    old[1].rx_bytes = 2**32 - 124_999_000
    new = model.build_ports(tables, {}, {})
    model.add_rates(new, old, 1.0, counter_bits=32)
    assert new[1].rx_rate == 1000.0  # 125 000 000 bytes in a second


def test_64_bit_counter_drop_gives_no_rate():
    old = model.build_ports(_tables(), {}, {})
    tables = _tables()
    tables["rx"]["1"] = 10
    new = model.build_ports(tables, {}, {})
    model.add_rates(new, old, 1.0, counter_bits=64)
    assert new[1].rx_rate is None


def test_discards_are_read_and_default_to_zero():
    tables = _tables()
    tables["rx_disc"] = {"1": 7}
    ports = model.build_ports(tables, {}, {})
    assert (ports[1].rx_discards, ports[1].tx_discards) == (7, 0)
    assert model.build_ports(_tables(), {}, {})[1].rx_discards == 0  # a switch without the columns


def test_utilization_is_the_share_of_the_link_speed():
    old = model.build_ports(_tables(), {}, {})
    tables = _tables()
    tables["rx"]["1"] += 12_500_000  # 100 Mbit in one second on a 1000 Mbit/s link
    new = model.build_ports(tables, {}, {})
    model.add_rates(new, old, 1.0)
    assert new[1].rx_util == 10.0
    assert new[1].tx_util == 0.0


def test_utilization_needs_a_link_and_a_rate():
    assert model.utilization(None, 1000) is None
    assert model.utilization(5.0, 0) is None
    assert model.utilization(2000.0, 1000) == 100.0  # never above 100


def test_mac_ports_lists_every_mac_with_its_port():
    fdb = {"1.0.4.32.249.54.2": 1, "1.0.8.220.84.149.70": 2}
    ports = model.build_ports(_tables(), fdb, {"1": 1, "2": 2})
    data = model.SwitchData(uptime=0, description="", object_id="", ports=ports)
    assert data.mac_ports == {"00:04:20:f9:36:02": 1, "00:08:dc:54:95:46": 2}
