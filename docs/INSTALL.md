# Installation

WiFi-Evil-Twin is a Python orchestration layer around standard Linux wireless
tools. You need **both** Python 3.8+ and the native tools below.

## 1. Native dependencies (Debian/Ubuntu/Kali)

```bash
sudo apt update
sudo apt install -y python3 python3-pip
sudo apt install -y hostapd dnsmasq aircrack-ng mdk4 iw
```

`hostapd`   — rogue access point
`dnsmasq`   — DHCP + DNS for the rogue subnet
`aireplay-ng` / `mdk4` — deauthentication frames
`iw` / `airodump-ng`  — scanning

## 2. Python package

```bash
pip install -r requirements.txt
pip install -e .          # installs the `wifi-evil-twin` console script
```

Or simply run it as a module (no install needed):

```bash
python -m wifi_evil_twin version
```

## 3. Hardware

A wireless adapter capable of **monitor mode** and **AP mode** is required.
Many attacks need two interfaces (one to deauth, one to host the rogue AP):
e.g. `wlan0` for the AP and `wlan1` (monitor) for deauth.

## 4. Verify

```bash
python -m wifi_evil_twin version
python -m wifi_evil_twin run --dry-run --ssid Test   # prints planned commands
```

See `USAGE.md` for run recipes and `DISCLAIMER.md` before doing anything.
