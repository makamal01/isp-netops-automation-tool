# ISP NetOps Tool

## Product Overview

ISP NetOps Tool is a focused network operations application for Internet Service Providers, managed service providers, and NOC teams that need a safer and faster way to collect operational data from routers across multiple vendors.

The application lets an operator securely maintain a device inventory, run approved read-only commands across multiple routers, view results as they arrive, and produce evidence that can be attached to tickets, maintenance records, audits, and incident reviews.

It is designed for practical NOC work: repeatable command collection, multi-vendor access, controlled operator actions, and useful output that can be reviewed by engineers or processed later by automation.

## The Business Problem

Network teams often spend valuable time repeating the same checks on individual routers, copying terminal output into tickets, and manually formatting evidence for other teams. This creates several operational risks:

- Slow incident investigation
- Inconsistent command collection
- Copy-and-paste errors
- Difficulty comparing results across devices
- Limited visibility into which commands were run and when
- Unstructured evidence that is difficult to reuse
- Unnecessary exposure of engineers to disruptive commands

ISP NetOps Tool addresses this by turning common read-only checks into a controlled, repeatable workflow.

## Who It Is For

- Internet Service Providers
- Broadband and fiber operators
- Enterprise NOCs
- Managed network service providers
- Network deployment and field engineering teams
- Infrastructure operations teams
- Service assurance and support teams
- Network training and lab environments

## Core Value

### Faster network checks
Run the same command set against multiple devices concurrently instead of connecting to each router manually.

### Safer operations
Safe mode blocks common configuration and disruptive command patterns, helping prevent accidental changes during read-only investigations.

### Multi-vendor coverage
Use one workflow for supported Cisco, Huawei, and Nokia platforms instead of switching between separate tools.

### Better operational evidence
Keep structured output for analysis, raw output for troubleshooting, and a readable report for tickets and audits.

### Deployable on a laptop
The application is designed as a lightweight desktop tool that can run locally without requiring a server or browser platform.

## Current Features

### 1. Multi-vendor router access

The application currently supports these vendor profiles through SSH and Netmiko:

- Cisco IOS
- Cisco IOS-XE
- Cisco IOS-XR
- Cisco NX-OS
- Huawei VRP
- Nokia SR OS
- Nokia SR Linux

Vendor-specific connection mapping is handled by the application, while the operator works through one consistent interface.

### 2. Device inventory

Operators can manage devices from the application through **Devices** actions:

- Add a device
- Edit a device
- Remove a device
- Import devices from CSV
- Export device CSV template for spreadsheet-compatible bulk onboarding
- Select multiple devices for a run
- Store vendor, hostname or IP address, SSH port, username, password, and optional enable secret
- Validate hostnames, IP addresses, ports, vendors, usernames, and duplicate names before saving

CSV import supports larger starting inventories and reduces manual entry for onboarding.
The template can be opened in common spreadsheet applications and saved back
as CSV without adding a proprietary spreadsheet dependency to the desktop app.

### 3. Bulk command execution

Operators enter one command per line and select the devices to include. The application runs the commands concurrently using a bounded worker pool. Concurrency and per-command timeout are adjustable next to the Run button, so an operator can tune a run for a small lab or a large inventory without editing configuration files.

Typical use cases include:

- Software and platform verification
- Interface status checks
- Routing and neighbor checks
- Service assurance checks
- Incident triage
- Pre-maintenance health checks
- Post-maintenance validation
- Evidence collection for support tickets

Each device produces an individual result with status, duration, output, or an actionable error. A live progress indicator shows how many devices have completed, and how many succeeded or failed, as results stream in during the run.

Operators can cancel a run cooperatively. Devices that have not started are skipped, while an active SSH operation is allowed to finish or reach its timeout cleanly. Failed and cancelled devices can be retried using the same command set without rerunning successful devices - and without losing the successful devices' results, which stay available for review and export alongside the retried ones.

### 4. Safe mode

Safe mode is enabled by default. It filters command input for common configuration or disruptive operations, including patterns associated with:

- Configuration mode entry
- Reload and reboot operations
- Erase and delete operations
- Clear operations
- Shutdown operations
- Other potentially disruptive actions

This makes the current product well suited to read-only operational checks. Any future write-capable workflow should have a separate approval and authorization design.

### 5. Parsed command output

When a supported TextFSM template is available, command output is parsed into structured JSON-like records. For example, an interface command can become a list of interface records with fields such as:

- Interface name
- IP address
- Administrative or operational status
- Protocol status

A version command can expose fields such as:

- Software version
- Hostname
- Platform or hardware
- Serial number
- Uptime
- Reload reason
- Configuration register

When no parser is available, the application preserves the command response as readable text.

Parsed output is valuable for:

- Engineer review
- Comparisons between devices
- Future dashboards
- Inventory extraction
- Automation and validation workflows

### 6. Raw router output

The application also preserves the raw router response. Raw output is important because it retains the original device text, including details that a parser may not model.

Raw output is useful for:

- Troubleshooting
- Vendor support cases
- Incident evidence
- Audit records
- Verifying parser behavior
- Investigating commands without a template

Raw files use clear command boundaries:

```text
====================================
COMMAND: show ip int brief
====================================
<raw router response>
```

### 7. Operational reports and exports

Each completed run produces a report containing:

- UTC generation timestamp
- Operator name
- Safe-mode status
- Devices requested
- Successful device count
- Failed device count
- Commands executed
- Device name and host
- Success or failure status
- Execution duration
- Per-command output sections

An export creates separate files for each device:

```text
<device>.txt
<device>_parsed.txt
<device>_raw.txt
report.txt
```

The parsed file preserves command-delimited structured output, for example:

```text
--- show ip int brief ---
[
  {
    "interface": "GigabitEthernet1",
    "ip_address": "unassigned",
    "status": "up",
    "proto": "up"
  }
]
```

The raw file preserves the original router text. The combined report provides a human-readable operational summary.

### 8. JumpServer and bastion support

Many ISP environments restrict direct access to network devices. The application can route device sessions through an SSH jump server or bastion host.

The jump-server workflow supports:

- Enable or disable bastion routing
- Configure jump-server host and port
- Configure jump-server credentials
- Test jump-server connectivity
- Reuse one jump-server session during a bulk run
- Open proxied channels to individual devices

Each router still authenticates with its own device credentials.

SSH host keys are verified strictly. The application uses system SSH host keys and can use its local application `known_hosts` file; unknown keys are rejected instead of being trusted automatically.

An in-app enrollment workflow (**Host Keys > Trust SSH Host Key...**) lets an operator fetch the key a device or jump server presents - without authenticating or running any command, and optionally through the configured jump server - review its type and SHA256 fingerprint, and explicitly confirm trust before the application will use it. The confirmed key is recorded locally and the action is audit-logged.

### 9. Local authentication and MFA

The application includes local user authentication for a controlled desktop deployment:

- Local user accounts
- Bcrypt password hashing
- Optional TOTP-based MFA
- QR enrollment for authenticator applications
- Support for common authenticator applications such as Google Authenticator, Microsoft Authenticator, and Authy
- Failed-login lockout protection
- Role information for local accounts

### 10. Encrypted local credential storage

Device passwords, jump-server passwords, and MFA secrets are encrypted at rest using a locally generated Fernet key. Passwords for application users are stored as bcrypt hashes rather than reversible passwords.

The application keeps its local data under the Windows user application-data directory, including:

- User accounts
- Device inventory
- Jump-server configuration
- Encryption key
- Reports
- Audit log

Organizations should protect the workstation account and application-data directory according to their own security policy.

Local JSON and YAML stores are schema-checked during startup, and updates are written atomically to reduce the risk of partial files after an interruption. Invalid local data produces a clear application error instead of an unhandled traceback.

### 11. Audit logging

The application records operational security events such as:

- Account creation
- Login success and failure
- MFA events
- Password changes
- Device additions, edits, and removals
- Device imports
- Command-run start and completion
- Jump-server configuration
- Result exports

The local audit log rotates when it reaches its configured size limit and retains backup files.

### 12. Desktop deployment

The application can run directly from Python during development or be packaged as a standalone Windows executable with PyInstaller.

This supports practical deployment models such as:

- A NOC engineer workstation
- A field engineer laptop
- A controlled operations jump host
- A network lab workstation
- A portable incident-response toolkit

The application also includes mocked execution tests for cancellation and strict SSH settings, along with report and inventory validation tests, so key operational behavior can be checked without requiring a live router for every test run.

## Typical ISP Workflows

### Incident triage

1. Select affected routers.
2. Enter a standard diagnostic command set.
3. Run the commands concurrently.
4. Review successful and failed devices in the results table.
5. Inspect parsed output in the application.
6. Export raw output and the combined report for the incident ticket.

### Pre-maintenance checks

1. Select the maintenance scope.
2. Run approved read-only health commands.
3. Preserve the report as the pre-change baseline.
4. Perform the approved maintenance separately.
5. Repeat the same command set after maintenance.
6. Compare the two exported datasets during review.

### Post-maintenance validation

1. Run software, interface, routing, and service checks.
2. Identify devices with failed or unexpected results.
3. Attach the combined report to the change record.
4. Retain raw output for escalation or vendor support.

### Inventory collection

Run version, hardware, interface, and routing commands across a device group to build a reusable operational dataset.

## Output Strategy

The product intentionally keeps three output forms because they serve different operational purposes:

| Output | Primary use |
|---|---|
| Parsed device file | Automation, comparison, inventory, engineer review |
| Raw device file | Troubleshooting, audit evidence, vendor support |
| Combined report | Ticket attachments, change records, management review |

Keeping these separate prevents a readable report from replacing the original evidence and prevents raw CLI text from becoming the only data source for automation.

## Security Position

The current product is designed around controlled, read-only network operations:

- SSH is used for device access.
- Safe mode is enabled by default.
- User passwords are bcrypt-hashed.
- Device and MFA secrets are encrypted locally.
- MFA is available for local accounts.
- Failed login attempts trigger a temporary lockout.
- Audit events are written locally.
- Credentials are not intended to be included in reports.

Before production rollout, each ISP should define its own requirements for workstation hardening, SSH host-key verification, account lifecycle, backup, access reviews, and centralized logging.

## Deployment Model

The current product is a local desktop application. This is useful when an ISP wants network access and credentials to remain within a controlled operations workstation.

A future subscription or enterprise deployment could offer multiple packaging options:

- Single-user desktop license
- Team workstation deployment
- Centralized management edition
- Managed NOC service
- Private-cloud or on-premises deployment
- API and automation integration

These are product opportunities and are not all part of the current desktop implementation.

## Planned Product Opportunities

The following areas are natural extensions for future releases:

- Searchable output
- Device groups, tags, and filters
- Configurable command profiles
- JSON and CSV exports
- Report comparison and change detection
- Centralized user and role management
- Centralized audit logging
- Scheduled health checks
- Alerting and notifications
- API access for automation
- Dashboard views for device health
- Approval workflows for carefully controlled write operations
- Multi-site and multi-tenant administration

## Subscription Value for ISPs

A subscriber should gain value from the product through reduced manual effort, better evidence quality, and improved operational consistency.

Potential commercial value includes:

- Fewer repetitive SSH sessions during incidents
- Faster collection of evidence across a device estate
- More consistent NOC procedures
- Shorter time to identify device or interface problems
- Easier handoff between shifts and teams
- Better change-record documentation
- Reusable operational data for future automation
- Reduced risk of accidental commands during read-only checks
- Support for mixed-vendor network environments

The strongest value case is for teams that operate many routers, support multiple vendors, or regularly need repeatable evidence during incidents and maintenance windows.

## Product Positioning

ISP NetOps Tool is not intended to replace a full network-management platform, monitoring system, configuration-management system, or IT service-management platform. It is a focused operational command and evidence tool that can complement those systems.

Its practical position is between manual terminal work and a larger network-automation platform:

- Easier to deploy than a full management platform
- More consistent than manual SSH sessions
- Safer for read-only operations than unrestricted scripting
- More useful for evidence than transient terminal output
- A foundation for future automation and reporting capabilities

## Living Document

For day-to-day NOC operation, see the [NOC_OPERATOR_MANUAL.md](NOC_OPERATOR_MANUAL.md).
For engineering installation, architecture, troubleshooting, and extension guidance,
see the [DEVELOPER_TECHNICAL_GUIDE.md](DEVELOPER_TECHNICAL_GUIDE.md).

This document is maintained as the product evolves.

When a feature is added, update:

1. **Current Features** with what the product now does.
2. **Typical ISP Workflows** with the new operational use case.
3. **Security Position** if the feature changes access or data handling.
4. **Subscription Value for ISPs** with the customer benefit.
5. **Planned Product Opportunities** by removing completed items and adding the next opportunities.

## Current Product Status

The current implementation is a Windows-focused PySide6 desktop application with local storage, SSH-based multi-vendor execution, live per-device run progress, safe-mode filtering, jump-server support, in-app SSH host-key enrollment, parsed and raw output preservation, local authentication, MFA, audit logging, and text-based operational exports.
