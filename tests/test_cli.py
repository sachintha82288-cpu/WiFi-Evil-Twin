"""Tests for CLI argument handling and config building."""

import pytest

from wifi_evil_twin.cli import build_config, build_parser, main


def test_version(capsys):
    rc = main(["version"])
    assert rc == 0
    assert "WiFi-Evil-Twin" in capsys.readouterr().out


def test_run_parser_requires_subcommand():
    with pytest.raises(SystemExit):
        main([])


def test_build_config_defaults():
    cfg = build_config(_ns(command="run"))
    assert cfg.ssid  # non-empty default


def test_build_config_overrides():
    ns = _ns(command="run", ssid="MyNet", channel=9, encryption="open",
             interface="wlan2", dry_run=True)
    cfg = build_config(ns)
    assert cfg.ssid == "MyNet"
    assert cfg.channel == 9
    assert cfg.interface == "wlan2"
    assert cfg.dry_run is True


def test_build_config_from_file(tmp_path):
    path = tmp_path / "c.json"
    path.write_text('{"ssid": "FromFile", "channel": 3}')
    ns = _ns(command="run", config=str(path))
    cfg = build_config(ns)
    assert cfg.ssid == "FromFile"
    assert cfg.channel == 3


def _ns(**kw):
    import argparse
    ns = argparse.Namespace()
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns
