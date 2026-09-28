# Changelog

All notable changes to ISP NetOps Tool are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/); versions map to
git tags so a build (and its `.exe`) can always be traced back to the exact
commit it came from.

## [Unreleased]

### Added
- **Reset** button to clear the device status table and output between runs.
- **Refresh** button above the Output pane to redisplay the selected
  device's stored output.
- Vendor filter (with **Cisco (all)** style brand groups) and name/IP
  search above the device list. **Select All** / **Select None** now act
  only on the devices shown.
- Live **Selected:** summary under the device list with a per-vendor count
  and a warning when checked devices are hidden by the filter.
- **Mixed vendors selected** prompt before a run whose devices span more
  than one brand: run on all, keep only one brand, or cancel.

### Fixed
- Clicking **Run** a second time did nothing: the new run never started
  and the previous run's status and output stayed on screen.
- Adding, editing, removing, or importing devices unchecked every device
  in the list. Checks are now kept (and follow a renamed device).

## [0.1.0] - 2026-09-15

First tagged baseline. A Windows desktop app for NOC/network engineers to
run bulk read-only commands across multi-vendor routers, plus a layered
MPLS/VPN path validation tool.

### Added
- Desktop GUI (PySide6) for bulk SSH command execution across Cisco,
  Huawei, and Nokia devices concurrently, with adjustable concurrency and
  per-command timeout.
- Local operator accounts (bcrypt) with optional TOTP MFA.
- Encrypted device inventory with CSV bulk import/export.
- Optional SSH JumpServer/bastion routing, with in-app fetch/trust
  enrollment for SSH host keys (fingerprint review before trusting,
  audit-logged).
- Safe mode: blocks obvious config/disruptive commands by default.
- Layered MPLS/VPN path validation (IGP -> MPLS -> LSP -> BGP -> MP-BGP/VPN)
  against real devices, with per-device pass/fail evidence.
- Live per-device progress during a run; failed devices can be retried
  without losing already-successful results.
- Parsed (TextFSM), raw, and combined-report exports for tickets/audits.
- Local audit logging of logins, MFA, device/inventory changes, and runs.
- App icon and a `.spec`-based Windows packaging build.

### Fixed
- Retrying failed devices no longer discarded the successful devices'
  results from the table and export.
- Safe mode no longer blocks ordinary read-only commands that merely
  mention a blocked word in a `| include` display filter, and now
  correctly blocks `configure terminal` (previously only matched `conf`,
  `conf t`, or `config`).
- BGP validation misread the standard `Up/Down` column in
  `show/display bgp summary` output as a failed peer on every vendor,
  even for a healthy Established session.
- Removed a validation-engine code path that could fabricate a "passed"
  result without checking any real device.
- Device connection failures now get consistent, actionable messages
  (auth/timeout/host-key/unexpected) instead of an uncategorized one for
  anything outside the first few known exception types.
