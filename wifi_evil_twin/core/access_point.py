"""Rogue access point via ``hostapd``.

Generates a ``hostapd.conf`` from the run :class:`Config` and launches
``hostapd`` as a managed background process. Supports open and WPA2 networks.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List, Optional

from wifi_evil_twin.config import Config
from wifi_evil_twin.exceptions import ConfigError
from wifi_evil_twin.utils.system import require_binaries, run

HOSTAPD_TEMPLATE = """\
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode={hw_mode}
channel={channel}
macaddr_acl=0
ignore_broadcast_ssid=0
{wpa_block}"""

WPA_BLOCK = """\
auth_algs=1
wpa=2
wpa_passphrase={wpa_passphrase}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
"""


def _hw_mode(channel: int) -> str:
    return "a" if channel > 14 else "g"


def render_hostapd_conf(cfg: Config) -> str:
    """Render a hostapd configuration string from *cfg*."""
    if cfg.encryption == "wpa2":
        wpa = WPA_BLOCK.format(wpa_passphrase=cfg.wpa_passphrase)
    else:
        wpa = "auth_algs=1\n"
    return HOSTAPD_TEMPLATE.format(
        interface=cfg.interface,
        ssid=cfg.ssid,
        hw_mode=_hw_mode(cfg.channel),
        channel=cfg.channel,
        wpa_block=wpa,
    )


def write_hostapd_conf(cfg: Config, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_hostapd_conf(cfg))
    return path


def start_ap(cfg: Config, *, dry_run: bool = False) -> "subprocess.Popen | object":
    """Launch hostapd for the rogue AP. Returns the process handle."""
    if not dry_run:
        require_binaries(["hostapd"])
    cfg.validate()
    tmp = tempfile.mkdtemp(prefix="wet-ap-")
    conf = os.path.join(tmp, "hostapd.conf")
    write_hostapd_conf(cfg, conf)
    cmd = ["hostapd", "-B", conf]
    if dry_run:
        print(f"[dry-run] $ {' '.join(cmd)}  (config at {conf})")
        return _DummyProc(cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc


class _DummyProc:
    def __init__(self, cmd: List[str]):
        self.args = cmd
        self.returncode = None

    def terminate(self):  # pragma: no cover
        pass

    def kill(self):  # pragma: no cover
        pass

    def wait(self, timeout: float = 0) -> int:  # pragma: no cover
        return 0
