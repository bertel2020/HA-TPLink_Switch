"""The translations and icons cover every entity the integration creates."""

import json
from pathlib import Path
import re

BASE = Path(__file__).parents[1] / "custom_components/tplink_switch_snmp"


def _keys(platform: str) -> set[str]:
    source = (BASE / f"{platform}.py").read_text()
    return set(re.findall(r'translation_key(?:\s*=\s*|=)"(\w+)"', source))


def _load(path: str) -> dict:
    return json.loads((BASE / path).read_text())


def test_every_entity_has_a_name_in_both_languages_and_in_strings() -> None:
    for platform in ("sensor", "binary_sensor"):
        keys = _keys(platform)
        assert keys, platform
        for path in ("strings.json", "translations/de.json", "translations/en.json"):
            names = _load(path)["entity"][platform]
            assert keys <= set(names), (path, platform, keys - set(names))
            assert all("name" in names[k] for k in keys)


def test_every_entity_has_an_icon() -> None:
    icons = _load("icons.json")["entity"]
    for platform in ("sensor", "binary_sensor"):
        keys = _keys(platform)
        assert keys <= set(icons[platform]), (platform, keys - set(icons[platform]))
        assert all("default" in icons[platform][k] for k in keys)


def test_the_uptime_sensor_has_a_name() -> None:
    # it is built without a description, so the key is set as an attribute
    for path in ("strings.json", "translations/de.json", "translations/en.json"):
        assert "uptime" in _load(path)["entity"]["sensor"]


def test_both_languages_have_the_same_keys() -> None:
    def shape(value):
        return {k: shape(v) for k, v in value.items()} if isinstance(value, dict) else None

    assert shape(_load("translations/de.json")) == shape(_load("translations/en.json"))
    assert shape(_load("strings.json")) == shape(_load("translations/de.json"))


def test_every_config_flow_field_is_explained() -> None:
    for path in ("strings.json", "translations/en.json"):
        for name, step in _load(path)["config"]["step"].items():
            assert set(step["data"]) <= set(step["data_description"]), (path, name)
