"""Configuration model for WiFi-Evil-Twin.

A single :class:`Config` object drives every module: the rogue AP, the DHCP/DNS
server, the firewall rules and the captive portal. It can be loaded from / saved
to a JSON file so runs are reproducible and auditable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


DEFAULTS: Dict[str, Any] = {
    "ssid": "Free-Public-WiFi",
    "interface": "wlan0",
    "monitor_interface": "wlan0",
    "channel": 6,
    "gateway_ip": "192.168.1.1",
    "netmask": "255.255.255.0",
    "dhcp_start": "192.168.1.10",
    "dhcp_end": "192.168.1.100",
    "lease_time": "12h",
    "encryption": "open",  # "open" or "wpa2"
    "wpa_passphrase": "password123",
    "portal_port": 8080,
    "portal_bind": "0.0.0.0",
    "scenario": "router",
    "deauth": False,
    "deauth_bssid": "",
    "deauth_client": "",  # "" = all clients
    "deauth_packets": 0,  # 0 = continuous until stopped
    "dry_run": False,
    "data_dir": "data",
    "log_file": "wifi_evil_twin.log",
    "redirect_https": True,
}


@dataclass
class Config:
    """Runtime configuration for an Evil Twin run."""

    ssid: str = DEFAULTS["ssid"]
    interface: str = DEFAULTS["interface"]
    monitor_interface: str = DEFAULTS["monitor_interface"]
    channel: int = DEFAULTS["channel"]
    gateway_ip: str = DEFAULTS["gateway_ip"]
    netmask: str = DEFAULTS["netmask"]
    dhcp_start: str = DEFAULTS["dhcp_start"]
    dhcp_end: str = DEFAULTS["dhcp_end"]
    lease_time: str = DEFAULTS["lease_time"]
    encryption: str = DEFAULTS["encryption"]
    wpa_passphrase: str = DEFAULTS["wpa_passphrase"]
    portal_port: int = DEFAULTS["portal_port"]
    portal_bind: str = DEFAULTS["portal_bind"]
    scenario: str = DEFAULTS["scenario"]
    deauth: bool = DEFAULTS["deauth"]
    deauth_bssid: str = DEFAULTS["deauth_bssid"]
    deauth_client: str = DEFAULTS["deauth_client"]
    deauth_packets: int = DEFAULTS["deauth_packets"]
    dry_run: bool = DEFAULTS["dry_run"]
    data_dir: str = DEFAULTS["data_dir"]
    log_file: str = DEFAULTS["log_file"]
    redirect_https: bool = DEFAULTS["redirect_https"]

    # ---- persistence -------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    # ---- helpers -----------------------------------------------------
    def captures_path(self) -> str:
        return os.path.join(self.data_dir, "captures.json")

    def captures_csv_path(self) -> str:
        return os.path.join(self.data_dir, "captures.csv")

    def ensure_dirs(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)

    def validate(self) -> None:
        if not (1 <= int(self.channel) <= 14):
            raise ValueError("channel must be between 1 and 14")
        if self.encryption not in ("open", "wpa2"):
            raise ValueError("encryption must be 'open' or 'wpa2'")
        if self.encryption == "wpa2" and len(self.wpa_passphrase) < 8:
            raise ValueError("wpa2 passphrase must be at least 8 characters")
        if not (1 <= int(self.portal_port) <= 65535):
            raise ValueError("portal_port out of range")
        if self.deauth and not self.deauth_bssid:
            raise ValueError("deauth requires deauth_bssid")
