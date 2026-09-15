# ISP NetOps Tool

For the ISP-facing product overview, capabilities, use cases, security position,
and evolving roadmap, see [ISP_NETOPS_PRODUCT_OVERVIEW.md](ISP_NETOPS_PRODUCT_OVERVIEW.md).
For the step-by-step NOC operating procedure, see [NOC_OPERATOR_MANUAL.md](NOC_OPERATOR_MANUAL.md).
For architecture, installation, troubleshooting, testing, and extension guidance,
see [DEVELOPER_TECHNICAL_GUIDE.md](DEVELOPER_TECHNICAL_GUIDE.md).

A lightweight, deployable-on-a-laptop desktop app for NOC/network engineers
to run **bulk show/read-only commands** across multiple routers from
different vendors (Cisco, Huawei, Nokia) at the same time.

## Features

- **Desktop GUI** (PySide6/Qt) — no server or browser required.
- **Login with local accounts** (bcrypt-hashed passwords) and optional
  **MFA** (TOTP, compatible with Google Authenticator / Microsoft
  Authenticator / Authy) — scan a QR code once to enroll.
- **Multi-vendor** via [Netmiko](https://github.com/ktbyers/netmiko):
  - Cisco IOS / IOS-XE / IOS-XR / NX-OS
  - Huawei VRP
  - Nokia SR OS (classic) and SR Linux
- **Bulk execution** against any number of devices concurrently
  (thread pool, tested conceptually up to ~100+ devices; today configured
  for 1 device per vendor as a starting inventory).
- **Safe mode** blocks obvious config/disruptive commands (e.g.
  `configure`, `reload`, `write erase`, `delete`) so the tool stays
  read-only for now, even if someone pastes the wrong command.
- **Encrypted local storage** — device passwords and MFA secrets are
  encrypted at rest (Fernet/AES) using a key generated on first run.
- **Export** per-device command output to text files for tickets/reports.

## Project layout

```
app/
  main.py              # entry point
  config.py            # app data dir / file paths
  auth/                # login + MFA
  core/                # device inventory, vendor mapping, command runner, safety filter
  gui/                 # PySide6 windows/dialogs
  utils/crypto.py       # local encryption helper
requirements.txt
```

Local data (users, device inventory, encryption key) is stored per-user in:
- Windows: `%APPDATA%\ISPNetOpsTool\`

## Setup (development)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

On first run you'll be asked to create the first admin account, then
optionally enroll MFA (QR code shown in-app).

## Adding devices

Use **Devices > Add Device** in the app. For a quick start with one
device per vendor:

| Field | Cisco example | Huawei example | Nokia example |
|---|---|---|---|
| Vendor | Cisco IOS | Huawei VRP | Nokia SR OS |
| Host | 10.0.0.1 | 10.0.0.2 | 10.0.0.3 |
| Username/Password | your creds | your creds | your creds |
| Enable/Secret | enable password (optional) | n/a | n/a |

Commands are entered one per line, e.g.:
```
show version
show ip interface brief
```
For Huawei, use `display` instead of `show` (e.g. `display version`).

### Bulk device import (CSV)

Use **Devices > Export device CSV template...** to create a header-only
spreadsheet template. Open it in Excel, LibreOffice, or Google Sheets, fill in
the device rows, save it as CSV, and use **Devices > Import Devices from CSV...**
to add many devices at once (e.g. toward 100 routers). Required columns:
`name,host,vendor,username,password`.
Optional columns: `port` (default 22), `secret` (enable/privileged password).
`vendor` must exactly match one of: `Cisco IOS`, `Cisco IOS-XE`, `Cisco IOS-XR`,
`Cisco NX-OS`, `Huawei VRP`, `Nokia SR OS`, `Nokia SR Linux`. Example:

```csv
name,host,vendor,username,password,port
core-rtr-01,10.0.0.1,Cisco IOS,admin,MyPassword,22
edge-hw-01,10.0.0.2,Huawei VRP,admin,MyPassword,22
edge-nokia-01,10.0.0.3,Nokia SR OS,admin,MyPassword,22
```

The import validates hosts, ports, vendors, required fields, and duplicate
device names before storing credentials encrypted in the local inventory.
Treat the completed CSV as sensitive because it contains passwords, and delete
or secure it after import according to your ISP's data-handling policy.

## JumpServer / bastion support

Many NOC environments only allow direct SSH to a jump server, which in
turn reaches the routers. Configure this under **JumpServer > Configure
JumpServer...**:

- **Route device connections through jump server** — toggle on/off.
- **Host/Port/Username/Password** — credentials for the jump server.
- **Test Connection** — verifies login to the jump server without running
  any device commands.

When enabled, the app logs into the jump host **once per run** and opens
one proxied SSH channel per device through it (standard SSH bastion/proxy
pattern) — each router still authenticates with its own credentials from
the device inventory. The jump server's credentials/config are encrypted at
rest the same way device passwords are.

## Results and reporting

- Each run's per-device output is shown in the **Output** pane (click a row
  in the results table).
- A combined, human-readable **text report** (run metadata, safe-mode
  status, commands, and per-device output) is automatically saved after
  every run to `%APPDATA%\ISPNetOpsTool\reports\run_<timestamp>.txt` — no
  manual step required, useful for after-the-fact audit/ticket evidence.
- Click **Export results...** to save a summary report plus separate parsed
  and raw files per device to a folder of your choice.
- Command output is parsed with TextFSM (`ntc-templates`) when a matching
  template exists, giving structured, readable fields instead of raw CLI
  text; it falls back to raw output automatically when no template matches.

## Safety

"Safe mode" (checked by default) rejects commands that look like
configuration or disruptive operations (config mode entry, reload,
reboot, erase, delete, clear, shutdown, etc.) across all three vendors'
syntaxes. This keeps the tool read-only for the current use case. It can
be unchecked later once config-command support is intentionally added,
but that should come with its own review/approval workflow.

## Packaging as a standalone Windows app

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --onefile --name ISP-NetOps-Tool ^
  --collect-all netmiko --collect-all ntc_templates ^
  app/main.py
```

The resulting `dist\ISP-NetOps-Tool.exe` can be copied to any Windows
laptop — it doesn't need Python installed. App data (users/devices/keys)
is still created fresh per machine under `%APPDATA%\ISPNetOpsTool\`, so
each laptop has its own local account store and device inventory unless
you deliberately share the `devices.yaml`/`users.json`/`secret.key` files
(not recommended — `secret.key` must stay private).

## Scaling to ~100 devices

- `run_bulk()` in `app/core/command_runner.py` uses a `ThreadPoolExecutor`
  so runs against many devices happen in parallel rather than one-by-one.
  Adjust **Max concurrent** and **Timeout (s)** next to the Run button if
  your network/CPU can handle more (or needs fewer) concurrent SSH sessions.
- Use **Devices > Import Devices from CSV...** to add many devices at once
  instead of one at a time (see "Bulk device import (CSV)" above).

## Security notes

- Passwords are hashed with bcrypt; device credentials and MFA secrets
  are encrypted at rest with a locally generated Fernet key
  (`%APPDATA%\ISPNetOpsTool\secret.key`). Protect that file/folder like
  any other credential store (it's per-machine, not versioned/committed).
- MFA uses standard TOTP (RFC 6238), no third-party service required.
- SSH is used for all vendor connections (via Netmiko); no cleartext
  Telnet is configured by default.
- Accounts lock for 15 minutes after 5 failed login attempts.
- All logins, MFA events, password changes, device inventory changes, and
  command runs are written to an audit log at
  `%APPDATA%\ISPNetOpsTool\isp_netops_tool.log` (rotates at 5MB, keeps 5
  backups).

