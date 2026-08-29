# WiFi-Evil-Twin

> A framework for performing **Evil Twin / rogue-access-point** attacks for
> authorized WiFi security testing and education.

WiFi-Evil-Twin orchestrates standard Linux wireless tools behind a clean Python
CLI and a web-based captive portal. It builds a rogue AP that mimics a target
network, optionally deauthenticates real clients so they roam onto the twin,
and captures any credentials submitted to the fake login page — storing them
locally for the operator to review.

---

## ⚠️ Legal & Responsible Use

This software is a **dual-use security tool**. You may use it **only** on
networks you own or have **written permission** to test. Unauthorized use is
illegal and unethical. The operator is solely responsible for complying with
all applicable laws.

The tool enforces an authorization gate: every radio-touching command refuses
to run until you acknowledge authorized use (set `WET_ACK_AUTH=1` for
non-interactive use). See [`DISCLAIMER.md`](DISCLAIMER.md).

---

## Features

- **Modular CLI** — `scan`, `deauth`, `ap`, `portal`, `run`, `creds`, `version`.
- **Scanner** — enumerate nearby APs (SSID/BSSID/channel/signal/encryption)
  via `airodump-ng` or `iw`.
- **Deauthenticator** — kick clients off a target AP with `aireplay-ng`/`mdk4`.
- **Rogue AP** — `hostapd` with open or WPA2 security, generated from config.
- **DHCP/DNS** — `dnsmasq` serves the rogue subnet.
- **Firewall** — `iptables` NAT + redirect of HTTP/HTTPS to the portal, with
  clean teardown.
- **Captive portal** — Flask app with switchable scenarios (`router`,
  `generic`, `social`); answers captive-probe URLs so devices show "connected".
- **Local credential store** — captures written to `data/captures.json` +
  `.csv`; nothing leaves the machine.
- **Dry-run mode** — `--dry-run` prints the exact commands/iptables rules
  without executing anything (no root, no hardware required).
- **Configurable & reproducible** — full run config serializable to JSON.

See [`FEATURES.md`](FEATURES.md) for the full plan and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for internals.

---

## Quick start

```bash
pip install -r requirements.txt
python -m wifi_evil_twin version
python -m wifi_evil_twin run --dry-run --ssid Test   # see what it would do
```

Real usage requires root and the native tools (see below).

### Install native tools (Debian/Ubuntu/Kali)

```bash
sudo apt install -y hostapd dnsmasq aircrack-ng mdk4 iw
```

### Full run (authorized target only)

```bash
sudo WET_ACK_AUTH=1 python -m wifi_evil_twin run \
    --ssid "Free-Public-WiFi" \
    --interface wlan0 --monitor-interface wlan1 --channel 6 \
    --scenario router \
    --deauth --deauth-bssid 00:11:22:33:44:55
```

Captured credentials land in `data/captures.json` / `data/captures.csv`.

```bash
sudo python -m wifi_evil_twin creds            # list
sudo python -m wifi_evil_twin creds --export out.csv
```

Full recipes: [`docs/INSTALL.md`](docs/INSTALL.md), [`docs/USAGE.md`](docs/USAGE.md).

---

## Project layout

```
wifi_evil_twin/
├── cli.py              CLI entrypoint (argparse subcommands)
├── config.py           Config dataclass (JSON serializable)
├── core/
│   ├── scanner.py      network enumeration + parsers
│   ├── deauth.py       deauth frame generation/execution
│   ├── access_point.py hostapd launch
│   ├── dhcp.py         dnsmasq launch
│   ├── firewall.py     iptables NAT + redirect (teardown)
│   ├── captive_portal.py  Flask app + scenarios
│   ├── credentials.py  local credential store
│   └── orchestrator.py lifecycle coordinator
├── utils/              system helpers + disclaimer gate
├── templates/          login_*.html, success.html
└── static/             style.css
tests/                  unit + integration (dry-run / Flask test client)
docs/                   INSTALL, USAGE, ARCHITECTURE
config/example.json     sample run config
```

---

## Testing

```bash
pip install pytest
python -m pytest -q
```

The suite covers config, credential store, scanner parsers, the captive
portal (via Flask test client), and config-generation — all without hardware.

---

## License

MIT — see [`LICENSE`](LICENSE).
