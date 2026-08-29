"""WiFi network scanner.

Enumerates nearby access points and parses them into structured
:class:`Network` objects. Uses ``airodump-ng`` when available (richest output)
and falls back to ``iw scan``.
"""

from __future__ import annotations

import csv
import io
import os
import re
import tempfile
import time
from dataclasses import dataclass
from typing import List, Optional

from wifi_evil_twin.utils.system import require_binaries, run


@dataclass
class Network:
    """A discovered wireless network."""

    bssid: str
    ssid: str
    channel: int
    signal: int  # dBm (negative; closer to 0 = stronger)
    encryption: str  # e.g. "WPA2", "WPA/WPA2", "OPEN", "WEP"
    frequency: str = ""

    def __str__(self) -> str:
        return (
            f"{self.ssid or '<hidden>':<24} {self.bssid:<19} "
            f"ch{self.channel:<3} {self.signal:>4}dBm {self.encryption}"
        )


# --------------------------------------------------------------------------
# Pure parsers (unit tested without hardware)
# --------------------------------------------------------------------------
def parse_airodump_csv(text: str) -> List[Network]:
    """Parse the CSV produced by ``airodump-ng --output-format csv``.

    The file has two sections: an ``Station MAC`` block and an AP block. We
    only care about the AP block (the first table before the station header).
    """
    nets: List[Network] = []
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    for row in rows:
        if not row:
            continue
        # The station section starts with this header.
        if row[0].strip().startswith("Station MAC"):
            break
        if row[0].strip().lower().startswith("bssid"):
            continue  # header row
        try:
            bssid = row[0].strip()
            if not bssid or bssid == "BSSID":
                continue
            # Columns: BSSID, First time seen, Last time seen, channel,
            # Speed, Privacy, Cipher, Authentication, Power, #beacons,
            # #data, #/s, Last seq, ESSID (may contain commas -> rest).
            channel = int(row[3].strip() or 0)
            power = int(row[8].strip() or -100)
            privacy = row[5].strip()
            # ESSID is the last column in airodump's CSV; strip quotes.
            essid = row[-1].strip().strip('"') if len(row) > 13 else ""
            nets.append(
                Network(
                    bssid=bssid,
                    ssid=essid,
                    channel=channel,
                    signal=power,
                    encryption=privacy or "UNKNOWN",
                )
            )
        except (IndexError, ValueError):
            continue
    return nets


def parse_iw_scan(text: str) -> List[Network]:
    """Parse ``iw dev <iface> scan`` output into networks.

    Handles multiple BSS blocks separated by ``BSS <mac>(on <iface>)``.
    """
    nets: List[Network] = []
    blocks = re.split(r"BSS ([0-9a-fA-F:]{17})", text)
    # blocks[0] is preamble; then pairs of (mac, body)
    for i in range(1, len(blocks), 2):
        mac = blocks[i]
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        ssid = ""
        channel = 0
        freq = 0
        signal = -100
        enc = "OPEN"
        m = re.search(r"SSID:\s*(.+)", body)
        if m:
            ssid = m.group(1).strip()
        m = re.search(r"signal:\s*(-?\d+)", body)
        if m:
            signal = int(m.group(1))
        m = re.search(r"primary channel:(\d+)", body)
        if m:
            channel = int(m.group(1))
        m = re.search(r"freq:\s*(\d+)", body)
        if m:
            freq = int(m.group(1))
        if channel == 0 and freq:
            channel = _channel_from_freq(freq)
        if "RSN:" in body or "RSNA:" in body:
            enc = "WPA2"
        elif "WPA:" in body:
            enc = "WPA"
        elif "WEP" in body:
            enc = "WEP"
        nets.append(
            Network(
                bssid=mac,
                ssid=ssid,
                channel=channel,
                signal=signal,
                encryption=enc,
                frequency=str(freq) if freq else "",
            )
        )
    return nets


def _channel_from_freq(freq: int) -> int:
    """Best-effort channel number from a center frequency in MHz."""
    if 2412 <= freq <= 2484:
        return 14 if freq == 2484 else (freq - 2412) // 5 + 1
    if 4915 <= freq <= 4980:  # 5 GHz (20 MHz, UNII-1/2)
        return (freq - 4915) // 5 + 36  # approximate, step may vary
    if 5035 <= freq <= 5980:
        return (freq - 5000) // 5
    return 0


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def scan(
    interface: str,
    *,
    duration: int = 10,
    dry_run: bool = False,
    prefer: str = "auto",
) -> List[Network]:
    """Scan for nearby networks using airodump-ng (preferred) or iw.

    In ``dry_run`` mode the command is printed but not executed and an empty
    list is returned (no native tools required).
    """
    if prefer == "auto":
        prefer = "airodump" if _have("airodump-ng") else "iw"

    if dry_run:
        if prefer == "airodump":
            run(
                ["airodump-ng", interface, "-w", "/tmp/wet-scan", "--output-format", "csv"],
                dry_run=True,
            )
        else:
            run(["iw", "dev", interface, "scan"], dry_run=True)
        return []

    if prefer == "airodump":
        return _scan_airodump(interface, duration=duration, dry_run=dry_run)
    return _scan_iw(interface, dry_run=dry_run)


def _have(binary: str) -> bool:
    from wifi_evil_twin.utils.system import which

    return which(binary) is not None


def _scan_airodump(interface: str, *, duration: int, dry_run: bool) -> List[Network]:
    require_binaries(["airodump-ng"])
    tmp = tempfile.mkdtemp(prefix="wet-scan-")
    out_base = os.path.join(tmp, "scan")
    cmd = ["airodump-ng", interface, "-w", out_base, "--output-format", "csv"]
    run(cmd, dry_run=dry_run, check=False)
    if dry_run:
        return []
    # airodump writes <base>-01.csv (or -NN.csv). Wait for it.
    time.sleep(duration)
    csv_file = _find_airodump_csv(out_base)
    if not csv_file:
        return []
    with open(csv_file, "r", encoding="utf-8", errors="replace") as fh:
        return parse_airodump_csv(fh.read())


def _find_airodump_csv(base: str) -> Optional[str]:
    import glob

    matches = sorted(glob.glob(base + "*.csv"))
    return matches[0] if matches else None


def _scan_iw(interface: str, *, dry_run: bool) -> List[Network]:
    require_binaries(["iw"])
    res = run(["iw", "dev", interface, "scan"], dry_run=dry_run, check=False)
    if dry_run:
        return []
    return parse_iw_scan(res.stdout)
