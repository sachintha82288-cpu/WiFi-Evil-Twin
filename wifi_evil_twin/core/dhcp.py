"""DHCP + DNS server via ``dnsmasq`` for the rogue subnet.

Clients that join the rogue AP need an IP address, a gateway (the AP box) and
DNS. ``dnsmasq`` provides both and is pointed at the AP interface.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List

from wifi_evil_twin.config import Config
from wifi_evil_twin.utils.system import require_binaries

DNSMASQ_TEMPLATE = """\
interface={interface}
bind-interfaces
dhcp-range={dhcp_start},{dhcp_end},{lease_time}
dhcp-option=3,{gateway_ip}
dhcp-option=6,{gateway_ip}
server=8.8.8.8
server=1.1.1.1
log-queries
"""


def render_dnsmasq_conf(cfg: Config) -> str:
    return DNSMASQ_TEMPLATE.format(
        interface=cfg.interface,
        dhcp_start=cfg.dhcp_start,
        dhcp_end=cfg.dhcp_end,
        lease_time=cfg.lease_time,
        gateway_ip=cfg.gateway_ip,
    )


def write_dnsmasq_conf(cfg: Config, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_dnsmasq_conf(cfg))
    return path


def start_dhcp(cfg: Config, *, dry_run: bool = False):
    """Launch dnsmasq for the rogue subnet. Returns the process handle."""
    if not dry_run:
        require_binaries(["dnsmasq"])
    tmp = tempfile.mkdtemp(prefix="wet-dhcp-")
    conf = os.path.join(tmp, "dnsmasq.conf")
    pid = os.path.join(tmp, "dnsmasq.pid")
    write_dnsmasq_conf(cfg, conf)
    cmd = ["dnsmasq", "-C", conf, "-p", "5353", "-x", pid]
    if dry_run:
        print(f"[dry-run] $ {' '.join(cmd)}")
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
