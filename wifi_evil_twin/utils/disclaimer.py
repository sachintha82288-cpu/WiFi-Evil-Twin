"""Disclaimer rendering and acknowledgment gate.

The tool must never perform an attack unless the operator has explicitly
acknowledged that they are authorized to test the target network.
"""

from __future__ import annotations

from wifi_evil_twin.exceptions import NotAuthorizedError

DISCLAIMER_TEXT = """\
================================================================
  WiFi-Evil-Twin — AUTHORIZED USE ONLY
----------------------------------------------------------------
This tool builds a rogue access point and captive portal to test
how easily credentials can be harvested on untrusted networks.

You may ONLY use it on networks you OWN or have WRITTEN permission
to test. Unauthorized use is illegal and unethical.

By continuing you accept full responsibility for your actions and
agree to comply with all applicable laws.
================================================================"""

_ACK_ENV = "WET_ACK_AUTH"
_ACK_FILE = ".wet_ack"


def show_disclaimer() -> None:
    """Print the legal disclaimer to stdout."""
    print(DISCLAIMER_TEXT)


def _persisted_ack() -> bool:
    import os

    if os.environ.get(_ACK_ENV) == "1":
        return True
    try:
        with open(_ACK_FILE, "r", encoding="utf-8") as fh:
            return fh.read().strip() == "1"
    except OSError:
        return False


def _persist_ack() -> None:
    import os

    try:
        with open(_ACK_FILE, "w", encoding="utf-8") as fh:
            fh.write("1")
    except OSError:
        pass


def require_authorization(*, force: bool = False, persist: bool = True) -> None:
    """Gate that refuses to proceed unless authorization is acknowledged.

    Resolution order:
      1. ``WET_ACK_AUTH=1`` environment variable (CI / non-interactive).
      2. A persisted ``.wet_ack`` file.
      3. Interactive prompt (unless ``force``/non-tty).
    """
    if _persisted_ack():
        return

    if os_environ_ack() or force:
        if persist:
            _persist_ack()
        return

    show_disclaimer()
    try:
        answer = input("Type 'I AM AUTHORIZED' to continue: ").strip()
    except (EOFError, OSError):
        raise NotAuthorizedError(
            "Non-interactive session: set WET_ACK_AUTH=1 to acknowledge."
        )
    if answer != "I AM AUTHORIZED":
        raise NotAuthorizedError("Authorization not acknowledged. Aborting.")
    if persist:
        _persist_ack()


def os_environ_ack() -> bool:
    """Helper to read the env ack without importing os at module top."""
    import os

    return os.environ.get(_ACK_ENV) == "1"
