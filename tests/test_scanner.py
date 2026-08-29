"""Tests for scanner parsers (no hardware required)."""

from wifi_evil_twin.core.scanner import parse_airodump_csv, parse_iw_scan


AIRODUMP_SAMPLE = """\
BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, #beacons, #data, #/s, Last seq, ESSID
00:11:22:33:44:55, 2026-01-01 00:00:00, 2026-01-01 00:00:01,  6, 54, WPA2, CCMP, PSK, -50, 10, 2, 0, 1, HomeNet
AA:BB:CC:DD:EE:FF, 2026-01-01 00:00:00, 2026-01-01 00:00:01, 11, 54, WPA, CCMP, PSK, -70, 5, 0, 0, 0, "Coffee Shop"
BSSID, Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
AA:BB:CC:DD:EE:FF, 11:22:33:44:55:66, 2026-01-01 00:00:00, 2026-01-01 00:00:01, -60, 3, AA:BB:CC:DD:EE:FF,
"""


def test_parse_airodump_csv():
    nets = parse_airodump_csv(AIRODUMP_SAMPLE)
    assert len(nets) == 2
    by_bssid = {n.bssid: n for n in nets}
    assert by_bssid["00:11:22:33:44:55"].ssid == "HomeNet"
    assert by_bssid["00:11:22:33:44:55"].channel == 6
    assert by_bssid["00:11:22:33:44:55"].encryption == "WPA2"
    assert by_bssid["AA:BB:CC:DD:EE:FF"].ssid == "Coffee Shop"
    assert by_bssid["AA:BB:CC:DD:EE:FF"].encryption == "WPA"


IW_SAMPLE = """\
BSS 00:11:22:33:44:55 (on wlan0)
        last seen: 0 ms ago
        TSF: 0 usec
        freq: 2437
        beacon interval: 100 TUs
        signal: -55.00 dBm
        SSID: HomeNet
        RSNA: supported
BSS AA:BB:CC:DD:EE:FF (on wlan0)
        freq: 2462
        signal: -80.00 dBm
        SSID: OpenCafe
"""


def test_parse_iw_scan():
    nets = parse_iw_scan(IW_SAMPLE)
    assert len(nets) == 2
    by_bssid = {n.bssid: n for n in nets}
    assert by_bssid["00:11:22:33:44:55"].ssid == "HomeNet"
    assert by_bssid["00:11:22:33:44:55"].channel == 6  # 2437 MHz -> ch 6
    assert by_bssid["00:11:22:33:44:55"].encryption == "WPA2"
    assert by_bssid["00:11:22:33:44:55"].signal == -55
    assert by_bssid["AA:BB:CC:DD:EE:FF"].encryption == "OPEN"
