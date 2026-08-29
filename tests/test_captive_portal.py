"""Tests for the Flask captive portal (no network required)."""

import pytest
from flask import Flask

from wifi_evil_twin.config import Config
from wifi_evil_twin.core.captive_portal import create_app, get_scenario, SCENARIOS
from wifi_evil_twin.core.credentials import CredentialStore


@pytest.fixture
def app(tmp_path):
    cfg = Config(data_dir=str(tmp_path / "data"), scenario="router", ssid="TestSSID")
    store = CredentialStore(cfg.captures_path(), cfg.captures_csv_path())
    return create_app(cfg, store), store


def test_index_renders_login(app):
    flask_app, _ = app
    client = flask_app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"TestSSID" in resp.data
    assert b"username" in resp.data


def test_login_captures_and_redirects(app):
    flask_app, store = app
    client = flask_app.test_client()
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "hunter2"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/success")
    assert store.count() == 1
    rec = store.all()[0]
    assert rec.fields["username"] == "admin"
    assert rec.fields["password"] == "hunter2"
    assert rec.client_ip == "127.0.0.1"


def test_success_page(app):
    flask_app, _ = app
    resp = flask_app.test_client().get("/success")
    assert resp.status_code == 200
    assert b"connected" in resp.data.lower()


def test_captive_probe_endpoints(app):
    flask_app, _ = app
    client = flask_app.test_client()
    assert client.get("/generate_204").status_code == 204
    assert client.get("/hotspot-detect.html").status_code == 204
    ncsi = client.get("/ncsi.txt")
    assert ncsi.status_code == 200
    assert b"Microsoft NCSI" in ncsi.data


def test_json_capture(app):
    flask_app, store = app
    client = flask_app.test_client()
    resp = client.post(
        "/submit",
        json={"email": "x@y.z", "password": "pw"},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 302
    assert store.all()[0].fields["email"] == "x@y.z"


def test_unknown_scenario_raises():
    with pytest.raises(KeyError):
        get_scenario("nope")


def test_scenarios_registered():
    assert set(SCENARIOS) == {"router", "generic", "social"}
