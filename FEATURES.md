# WiFi-Evil-Twin — Feature Plan

> A framework for authorized Evil Twin / rogue-access-point security testing.
> For use only on networks you own or have written permission to test.

## 1. Goal
Build a modular, Python-based Evil Twin toolkit that orchestrates standard
Linux wireless tools (`hostapd`, `dnsmasq`, `aireplay-ng`/`mdk4`, `airodump-ng`)
behind a clean CLI, with a web-based captive portal that captures credentials
submitted by clients that associate with the rogue AP — for authorized testing
and education only.

## 2. Core Principles
- **Authorization gate:** A disclaimer must be acknowledged before any
  operation that touches the radio. The tool refuses to run attacks unless the
  operator confirms legal authorization.
- **Root + capability checks:** Refuses to run without privileges / required
  binaries, with helpful messages.
- **Dry-run mode:** Print the exact commands/iptables rules it *would* execute
  so behavior is auditable without hardware.
- **Safe by default:** No credential exfiltration off-box; captures are stored
  locally in the operator's control.

## 3. Feature Breakdown

### 3.1 CLI (`wifi_evil_twin/cli.py`)
- `scan`        — list nearby APs (SSID, BSSID, channel, signal, encryption)
- `deauth`      — send deauth frames to disconnect clients from a target AP
- `ap`          — start only the rogue access point
- `portal`      — start only the captive portal + DHCP/DNS on an existing AP
- `run`         — full orchestrated attack (AP + DHCP/DNS + portal + optional deauth)
- `creds`       — list / export captured credentials
- `version`     — show version

### 3.2 Scanner (`core/scanner.py`)
- Uses `iw dev` / `airodump-ng` to enumerate networks.
- Parses output into structured `Network` objects.
- Filter by SSID / channel / signal.

### 3.3 Deauth (`core/deauth.py`)
- `aireplay-ng --deauth` and `mdk4` backoff options.
- Target a single client MAC or the whole BSSID.
- Rate / duration controls; `--dry-run` support.

### 3.4 Access Point (`core/access_point.py`)
- Generates `hostapd.conf` from a `Config` (SSID, channel, interface,
  encryption open/WPA2).
- Launches `hostapd` as a managed subprocess.
- Tears down cleanly on exit (signal handling).

### 3.5 DHCP/DNS (`core/dhcp.py`)
- Generates `dnsmasq.conf` (DHCP range, gateway, DNS).
- Launches `dnsmasq` bound to the AP interface.

### 3.6 Firewall (`core/firewall.py`)
- Sets up `iptables` NAT + redirect of all HTTP/HTTPS to the portal port.
- Clean rollback of rules on shutdown.

### 3.7 Captive Portal (`core/captive_portal.py`)
- Flask app served on the rogue AP's subnet.
- Multiple **scenarios/templates** (router login, generic, social).
- Captures `POST` credentials, stores them, then redirects to a benign page.
- Logs client IP, timestamp, user-agent, submitted fields.
- Session-aware so re-submissions are tracked.

### 3.8 Credential Store (`core/credentials.py`)
- `CredentialStore` appends records (json + csv).
- Fields: timestamp, scenario, client_ip, ssid, fields dict, user_agent.
- `list()` / `export_csv()` / `clear()`.

### 3.9 Orchestrator (`core/orchestrator.py`)
- Ties scanner→deauth→ap→dhcp→firewall→portal together.
- Lifecycle management, graceful shutdown, logs to file.

### 3.10 Utilities (`utils/`)
- `system.py` — root check, command runner (real + dry-run), interface
  enumeration, monitor-mode toggle.
- `disclaimer.py` — render + require acknowledgment of legal use.

## 4. Project Layout
```
WiFi-Evil-Twin/
├── README.md  FEATURES.md  DISCLAIMER.md  LICENSE
├── requirements.txt  setup.py  Makefile  .gitignore
├── wifi_evil_twin/
│   ├── __init__.py  __main__.py  cli.py  config.py  exceptions.py
│   ├── core/      (scanner, deauth, access_point, dhcp, firewall,
│   │               captive_portal, credentials, orchestrator)
│   ├── utils/     (system, disclaimer)
│   ├── templates/ (login_*.html, success.html)
│   ├── static/    (style.css)
│   └── config/    (hostapd.conf.template, dnsmasq.conf.template)
├── tests/         (unit + integration via dry-run / Flask test client)
└── docs/          (INSTALL, USAGE, ARCHITECTURE)
```

## 5. Milestones
1. Planning + scaffolding (this document, meta files). ✅
2. Core utilities + config + credential store (+ tests).
3. Scanner + deauth modules.
4. AP + DHCP + firewall modules.
5. Captive portal + templates.
6. Orchestrator + CLI wiring.
7. Docs + packaging + final test pass.

## 6. Out of Scope (for now)
- WPA2/Enterprise cracking (handled by external tools; we only rogue + capture).
- GUI; web dashboard for live creds (future enhancement).
- Automated phishing-kit downloads.
