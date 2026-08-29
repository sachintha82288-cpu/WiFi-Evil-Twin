"""Tests for the orchestration modules (conf generation, dry-run, lifecycle)."""

from wifi_evil_twin.config import Config
from wifi_evil_twin.core import access_point, dhcp, firewall
from wifi_evil_twin.core.deauth import build_command
from wifi_evil_twin.core.orchestrator import Orchestrator
from wifi_evil_twin.core.credentials import CredentialStore


# ---- deauth command building ------------------------------------------------
def test_build_command_aireplay_all():
    cmd = build_command(monitor_iface="wlan1", bssid="AA:11", packets=5)
    assert cmd[:3] == ["aireplay-ng", "--deauth", "5"]
    assert "-a" in cmd and "AA:11" in cmd
    assert "wlan1" == cmd[-1]


def test_build_command_aireplay_client():
    cmd = build_command(monitor_iface="wlan1", bssid="AA:11", client="BB:22")
    assert "-c" in cmd and "BB:22" in cmd


def test_build_command_mdk4():
    cmd = build_command(monitor_iface="wlan1", bssid="AA:11", tool="mdk4")
    assert cmd[0] == "mdk4"
    assert "d" in cmd


# ---- hostapd conf -----------------------------------------------------------
def test_hostapd_open():
    cfg = Config(ssid="OpenNet", channel=6, encryption="open", interface="wlan0")
    conf = access_point.render_hostapd_conf(cfg)
    assert "ssid=OpenNet" in conf
    assert "channel=6" in conf
    assert "wpa_passphrase" not in conf
    assert "hw_mode=g" in conf


def test_hostapd_wpa2():
    cfg = Config(ssid="SecNet", channel=40, encryption="wpa2", wpa_passphrase="12345678")
    conf = access_point.render_hostapd_conf(cfg)
    assert "wpa_passphrase=12345678" in conf
    assert "wpa=2" in conf
    assert "hw_mode=a" in conf  # 5 GHz channel


# ---- dnsmasq conf -----------------------------------------------------------
def test_dnsmasq_conf():
    cfg = Config(gateway_ip="192.168.1.1", dhcp_start="192.168.1.10",
                 dhcp_end="192.168.1.100", lease_time="12h", interface="wlan0")
    conf = dhcp.render_dnsmasq_conf(cfg)
    assert "interface=wlan0" in conf
    assert "dhcp-range=192.168.1.10,192.168.1.100,12h" in conf
    assert "dhcp-option=3,192.168.1.1" in conf


# ---- firewall dry-run -------------------------------------------------------
def test_firewall_dry_run_records_rules(monkeypatch, capsys):
    recorded = []

    def fake_run(args, **kwargs):
        recorded.append(args)
        from wifi_evil_twin.utils.system import RunResult
        return RunResult(args=list(args), returncode=0, dry_run=True)

    monkeypatch.setattr("wifi_evil_twin.core.firewall.run", fake_run)
    cfg = Config(dry_run=True, interface="wlan0", gateway_ip="192.168.1.1",
                 portal_port=8080, redirect_https=True)
    fw = firewall.Firewall(cfg, dry_run=True)
    fw.setup()
    joined = " ".join(" ".join(r) for r in recorded)
    assert "net.ipv4.ip_forward=1" in joined
    assert "MASQUERADE" in joined
    assert "--dport 80" in joined
    assert "--dport 443" in joined  # redirect_https


# ---- orchestrator lifecycle -------------------------------------------------
def test_orchestrator_init(tmp_path):
    cfg = Config(data_dir=str(tmp_path / "d"), dry_run=True)
    store = CredentialStore(cfg.captures_path(), cfg.captures_csv_path())
    orch = Orchestrator(cfg, store)
    assert orch.fw is not None
    assert orch.ap_proc is None


def test_orchestrator_stop_idempotent(tmp_path):
    cfg = Config(data_dir=str(tmp_path / "d"), dry_run=True)
    store = CredentialStore(cfg.captures_path(), cfg.captures_csv_path())
    orch = Orchestrator(cfg, store)
    orch.stop()  # should not raise even before start
