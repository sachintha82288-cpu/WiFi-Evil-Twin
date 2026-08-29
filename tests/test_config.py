"""Tests for the Config model."""

import json
import os

import pytest

from wifi_evil_twin.config import Config, DEFAULTS


def test_defaults_match_constants():
    cfg = Config()
    for k, v in DEFAULTS.items():
        assert getattr(cfg, k) == v


def test_round_trip_json(tmp_path):
    cfg = Config(ssid="TestNet", channel=11, encryption="wpa2", wpa_passphrase="sup3rs3cret")
    path = tmp_path / "cfg.json"
    cfg.save(str(path))
    loaded = Config.load(str(path))
    assert loaded.ssid == "TestNet"
    assert loaded.channel == 11
    assert loaded.encryption == "wpa2"
    assert loaded.wpa_passphrase == "sup3rs3cret"


def test_validate_ok():
    Config(encryption="open", channel=6, portal_port=8080).validate()


@pytest.mark.parametrize(
    "kw,err",
    [
        ({"channel": 99}, "channel"),
        ({"encryption": "wep"}, "encryption"),
        ({"encryption": "wpa2", "wpa_passphrase": "short"}, "8"),
        ({"portal_port": 70000}, "range"),
    ],
)
def test_validate_bad(kw, err):
    cfg = Config(**kw)
    with pytest.raises(ValueError, match=err):
        cfg.validate()


def test_paths(tmp_path):
    cfg = Config(data_dir=str(tmp_path / "d"))
    assert cfg.captures_path().endswith("captures.json")
    assert cfg.captures_csv_path().endswith("captures.csv")
    cfg.ensure_dirs()
    assert os.path.isdir(cfg.data_dir)
