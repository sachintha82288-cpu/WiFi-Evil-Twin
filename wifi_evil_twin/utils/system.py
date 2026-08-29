"""System-level helpers: privilege checks, command execution (real + dry-run),
interface enumeration and monitor-mode toggling.

Everything that touches the operating system goes through :func:`run` so that
a single ``dry_run`` flag makes the entire toolkit auditable without any
hardware or side effects.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable, List, Optional

from wifi_evil_twin.exceptions import (
    InterfaceError,
    MissingDependencyError,
    RootRequiredError,
)


@dataclass
class RunResult:
    """Captured result of a command execution (or a dry-run description)."""

    args: List[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    dry_run: bool = False


def is_root() -> bool:
    """Return True if the current process is running as root/UID 0."""
    return os.geteuid() == 0


def require_root() -> None:
    """Raise :class:`RootRequiredError` unless running as root."""
    if not is_root():
        raise RootRequiredError(
            "This operation requires root privileges. Re-run with: sudo "
            "python -m wifi_evil_twin ..."
        )


def which(binary: str) -> Optional[str]:
    """Return the absolute path of *binary* or ``None`` if not found."""
    return shutil.which(binary)


def require_binaries(binaries: Iterable[str]) -> None:
    """Ensure every binary in *binaries* is available on PATH."""
    missing = [b for b in binaries if which(b) is None]
    if missing:
        raise MissingDependencyError(
            "Missing required tool(s): " + ", ".join(missing) + ". "
            "Install them (e.g. apt install hostapd dnsmasq aircrack-ng "
            "mdk4) and retry."
        )


def run(
    args: List[str],
    *,
    dry_run: bool = False,
    capture: bool = True,
    check: bool = False,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: Optional[float] = None,
) -> RunResult:
    """Run *args* as a subprocess, or describe it when *dry_run* is set.

    When ``dry_run`` is True the command is NOT executed; instead a
    :class:`RunResult` is returned with ``dry_run=True`` and ``returncode=0``.
    This lets the orchestrator print exactly what it would do.
    """
    printable = " ".join(str(a) for a in args)
    if dry_run:
        print(f"[dry-run] $ {printable}")
        return RunResult(args=list(args), returncode=0, dry_run=True)

    proc = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    result = RunResult(
        args=list(args),
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
    if check and result.returncode != 0:
        raise MissingDependencyError(
            f"Command failed ({result.returncode}): {printable}\n"
            f"{result.stderr}"
        )
    return result


def list_wireless_interfaces() -> List[str]:
    """Return the names of available wireless interfaces via ``iw dev``."""
    out = run(["iw", "dev"], dry_run=False, check=False)
    if out.returncode != 0:
        # Fall back to /sys/class/ieee80211 if `iw` is unavailable.
        import glob

        return sorted(
            os.path.basename(p)
            for p in glob.glob("/sys/class/net/*/wireless")
        )
    ifaces: List[str] = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("Interface"):
            iface = line.split("Interface")[-1].strip()
            if iface:
                ifaces.append(iface)
    return ifaces


def interface_exists(iface: str) -> bool:
    """Return True if *iface* exists under /sys/class/net."""
    return os.path.exists(os.path.join("/sys/class/net", iface))


def require_interface(iface: str) -> None:
    """Raise :class:`InterfaceError` if *iface* is not present."""
    if not interface_exists(iface):
        available = ", ".join(list_wireless_interfaces()) or "none found"
        raise InterfaceError(
            f"Interface '{iface}' not found. Available wireless interfaces: "
            f"{available}."
        )


def set_monitor_mode(iface: str, enable: bool = True) -> str:
    """Put *iface* into (or out of) monitor mode.

    Returns the (possibly renamed) monitor interface name. Uses ``iw`` and
    falls back gracefully. This is a no-op under ``dry_run`` handled by the
    caller passing dry_run into :func:`run`.
    """
    mon_iface = iface
    if enable:
        run(["ip", "link", "set", iface, "down"])
        run(["iw", iface, "set", "monitor", "control"])
        run(["ip", "link", "set", iface, "up"])
        mon_iface = iface
    else:
        run(["ip", "link", "set", iface, "down"])
        run(["iw", iface, "set", "type", "managed"])
        run(["ip", "link", "set", iface, "up"])
    return mon_iface


def kill_network_manager() -> None:
    """Best-effort stop of services that fight for the wireless card."""
    for svc in ("NetworkManager", "wpa_supplicant"):
        run(["systemctl", "stop", svc], check=False)
