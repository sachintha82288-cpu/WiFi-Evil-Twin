"""Tests for the credential store."""

import csv
import json

from wifi_evil_twin.core.credentials import CredentialStore, CredentialRecord


def test_add_writes_json_and_csv(tmp_path):
    store = CredentialStore(
        str(tmp_path / "captures.json"), str(tmp_path / "captures.csv")
    )
    rec = store.add(
        scenario="router",
        client_ip="192.168.1.42",
        ssid="Free-WiFi",
        fields={"username": "admin", "password": "secret"},
        user_agent="curl/8",
        path="/login",
    )
    assert isinstance(rec, CredentialRecord)
    assert store.count() == 1

    # JSON lines file has one record.
    lines = (tmp_path / "captures.json").read_text().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["client_ip"] == "192.168.1.42"
    assert obj["fields"]["password"] == "secret"

    # CSV has one row per field.
    rows = list(csv.reader((tmp_path / "captures.csv").read_text().splitlines()))
    assert rows[0] == ["timestamp", "scenario", "client_ip", "ssid", "field", "value", "user_agent"]
    assert any(r[4] == "username" and r[5] == "admin" for r in rows[1:])
    assert any(r[4] == "password" and r[5] == "secret" for r in rows[1:])


def test_clear(tmp_path):
    store = CredentialStore(str(tmp_path / "captures.json"), str(tmp_path / "captures.csv"))
    store.add(scenario="x", client_ip="1.1.1.1", ssid="s", fields={"u": "p"})
    assert store.count() == 1
    store.clear()
    assert store.count() == 0
    assert (tmp_path / "captures.json").read_text().strip() == ""


def test_export_csv(tmp_path):
    store = CredentialStore(str(tmp_path / "captures.json"), str(tmp_path / "captures.csv"))
    store.add(scenario="router", client_ip="10.0.0.5", ssid="S", fields={"a": "b"})
    dest = tmp_path / "out.csv"
    store.export_csv(str(dest))
    assert dest.read_bytes() == (tmp_path / "captures.csv").read_bytes()
