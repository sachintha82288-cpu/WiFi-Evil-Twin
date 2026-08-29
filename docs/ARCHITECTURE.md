# Architecture

```
                 ┌─────────────────────────────────────────┐
                 │                CLI (cli.py)              │
                 │  scan | deauth | ap | portal | run | creds│
                 └───────────────┬─────────────────────────┘
                                 │ builds Config
            ┌────────────────────┼───────────────────────────┐
            │                    │                            │
      ┌─────▼─────┐       ┌──────▼───────┐            ┌───────▼──────┐
      │  scanner  │       │  deauth      │            │ Orchestrator │
      │ (iw/airod)│       │ (aireplay/mdk)│           │  (lifecycle) │
      └───────────┘       └──────────────┘            └───┬───┬───┬───┘
                                                          │   │   │
                                          ┌───────────────┘   │   └───────────────┐
                                    ┌─────▼─────┐      ┌──────▼─────┐      ┌───────▼──────┐
                                    │ access_pt │      │    dhcp    │      │   firewall   │
                                    │ (hostapd) │      │  (dnsmasq) │      │  (iptables)  │
                                    └───────────┘      └────────────┘      └──────────────┘
                                                        │
                                                  ┌─────▼─────┐
                                                  │  portal   │  Flask app, scenario templates
                                                  │ (captive) │  -> CredentialStore (local)
                                                  └───────────┘
```

## Data flow of a capture

1. Client associates with the rogue AP (`hostapd`).
2. `dnsmasq` hands out an IP; iptables redirects 80/443 to the portal port.
3. Client opens any site → Flask serves the scenario login page.
4. `POST /login` → `CredentialStore.add()` writes `captures.json` + `captures.csv`.
5. Client is redirected to a benign "connected" page.

## Design notes

- **Single source of truth:** `Config` (dataclass) drives every module and is
  serializable to JSON for reproducible runs.
- **Dry-run everywhere:** all side-effecting calls go through
  `utils.system.run(..., dry_run=...)`, so the entire toolkit is auditable with
  `--dry-run` and unit-testable without hardware.
- **Local-only data:** captured credentials never leave the box.
- **Authorization gate:** `utils.disclaimer.require_authorization()` must pass
  before any radio-touching command runs.
