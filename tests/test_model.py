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
    fdb = {"1.0.4.32.249.54.2": 7, "1.0.8.220.84.149.70": 7}
    ports = model.build_ports(_tables(), fdb, {"7": 1})
    assert ports[1].macs == ["00:04:20:f9:36:02", "00:08:dc:54:95:46"]
    assert ports[2].macs == []


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
