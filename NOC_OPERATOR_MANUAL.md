# ISP NetOps Tool
## NOC Operator Manual and Method of Procedure

**Document status:** Operational draft  
**Audience:** NOC engineers, network operations leads, and support engineers  
**Use case:** Controlled, read-only command collection from network devices

## 1. Purpose

This manual defines the standard procedure for using ISP NetOps Tool to collect repeatable operational information from routers across a multi-vendor ISP network.

Use this procedure for:

- Incident triage
- Pre-maintenance checks
- Post-maintenance validation
- Service-impact investigation
- Device inventory collection
- Ticket and change-record evidence

The current workflow is intended for read-only commands. Do not use it as a replacement for an approved change-management procedure.

## 2. Operating Principles

- Use the correct change, incident, or service ticket reference.
- Select only the devices within the approved scope.
- Use approved read-only commands.
- Keep Safe mode enabled unless an authorized policy explicitly says otherwise.
- Verify SSH host keys before connecting to a new server or router.
- Treat exported reports as operational evidence and protect them appropriately.
- Never place passwords, tokens, or private keys in reports or tickets.
- Escalate unexpected output, authentication failures, or host-key changes.

## 3. Prerequisites

Before starting, confirm:

- ISP NetOps Tool is installed and starts successfully.
- You have an authorized local application account.
- MFA is available if enabled.
- You have approved device credentials.
- You know whether direct access or the JumpServer is required.
- The workstation has network, VPN, or management-network access.
- The target router SSH port is reachable.
- Router and JumpServer host keys are trusted.
- You have the relevant ticket or maintenance reference.

## 4. First-Time Setup

### 4.1 Start the application

From the project or packaged application location, start the application using the approved deployment method. During development:

```powershell
.\.venv\Scripts\python.exe -m app.main
```

Create the first administrator account when prompted. Use a strong password and enable MFA when offered.

### 4.2 Configure SSH host-key trust

Host keys must be verified through an approved source before they are trusted. Do not blindly accept a changed key.

The application trust file is:

```text
%APPDATA%\ISPNetOpsTool\known_hosts
```

For a JumpServer, obtain the server host key from the server or an approved management workstation. For legacy Cisco devices, use the approved legacy SSH method on the JumpServer if modern `ssh-keyscan` cannot negotiate with the router.

A valid entry must contain the target address, key type, and public key, for example:

```text
10.246.222.2 ssh-rsa AAAA...
```

Do not copy SSH banners such as:

```text
# 10.246.222.2:22 SSH-1.99-Cisco-1.25
```

After adding keys, verify the trust file parses and contains the expected target entries. If a known key changes unexpectedly, stop and escalate to the network/security owner.

### 4.3 Configure the JumpServer

Open:

**JumpServer -> Configure JumpServer...**

Enter:

- Host/IP address
- SSH port, normally `22`
- JumpServer username
- JumpServer password

Select the routing option and click **Test Connection**. Do not proceed if the test fails.

The JumpServer provides network reachability. Each router still uses its own device credentials.

## 5. Add or Import Devices

### 5.1 Add one device

Open **Devices -> Add Device** and provide:

- Unique device name
- IP address or resolvable hostname
- Vendor profile
- SSH port
- Username
- Password
- Optional enable or privileged-mode secret

The application validates the host, port, vendor, required credentials, and duplicate name before saving.

### 5.2 Import devices from CSV

Use **Devices -> Export device CSV template...** first. Open the generated
template in Excel, LibreOffice, or Google Sheets, fill in the rows, save it as
CSV, and then use **Devices -> Import Devices from CSV...**.

Required columns:

```csv
name,host,vendor,username,password
```

Optional columns:

```csv
port,secret
```

Supported vendor values must match the application list exactly, including:

- Cisco IOS
- Cisco IOS-XE
- Cisco IOS-XR
- Cisco NX-OS
- Huawei VRP
- Nokia SR OS
- Nokia SR Linux

Protect the CSV because it contains credentials. Delete or securely handle the source CSV after import according to ISP policy.

The import validates hostnames/IP addresses, SSH ports, supported vendors,
required fields, and duplicate device names. Invalid rows are skipped and
listed in the import summary; valid rows are still imported.

## 6. Standard Run Procedure

1. Open the relevant incident, change, or service ticket.
2. Confirm the approved device scope.
3. Check the required devices in the device list.
4. Use **Select All** only when the entire displayed inventory is in scope.
5. Enter one approved command per line.
6. Confirm the command syntax matches the vendor.
   - Cisco/Nokia examples commonly use `show`.
   - Huawei examples commonly use `display`.
7. Keep **Safe mode** enabled.
8. Click **Run on selected devices**.
9. Monitor the results table.
10. Select a device row to inspect its Output pane.
11. Review failed devices separately from successful devices.
12. Use **Cancel** if the run scope is wrong or queued work must stop.
13. Use **Retry failed** only after checking the cause and confirming retry is appropriate.
14. Export results when the run is complete.
15. Attach the appropriate report to the ticket and record the run time and scope.

## 7. Recommended Read-Only Commands

Use only commands approved for the device and operational purpose.

### Cisco examples

```text
show version
show ip interface brief
show interfaces status
show ip route
show cdp neighbors
show lldp neighbors
show logging
```

### Huawei examples

```text
display version
display ip interface brief
display interface brief
display ip routing-table
display lldp neighbor
```

### Nokia examples

Use the approved SR OS or SR Linux command profile for the target platform. Do not assume Cisco syntax applies to Nokia devices.

## 8. Results and Output Handling

The application produces separate output forms:

### Parsed output

The parsed file uses command sections such as:

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

Use parsed output for structured review, comparison, inventory, and future automation.

### Raw output

The raw file preserves the router response using command headings:

```text
====================================
COMMAND: show ip int brief
====================================
<raw router response>
```

Use raw output for troubleshooting, vendor escalation, and evidence where the original device response matters.

### Combined report

The combined `report.txt` contains run metadata, operator, safe-mode status, device counts, device status, duration, and command output. Use it for tickets, change records, handovers, and audits.

## 9. Export Naming

An export directory contains files similar to:

```text
POC1-1.txt
POC1-1_parsed.txt
POC1-1_raw.txt
report.txt
```

Store exports in an approved location. Do not email reports containing sensitive operational information unless the approved secure process allows it.

## 10. Failure Handling

### No route to host or TCP timeout

- Confirm VPN or management-network access.
- Confirm the device address and port.
- Check firewall and routing policy.
- Test reachability from the JumpServer if routing through it.
- Escalate to the network-access owner if the path is unavailable.

### SSH host-key or protocol error

- Do not disable strict host-key verification as a shortcut.
- Confirm the target address.
- Check whether the device key changed legitimately.
- Add the verified key using the approved procedure.
- Escalate unexpected key changes as a security event.

### Authentication failed

- Confirm the correct device username and password.
- Confirm the account is authorized for SSH and the required command level.
- Do not repeatedly retry unknown credentials.
- Check for device-side account lockout or AAA failure.

### Command rejected by Safe mode

- Review the command for configuration or disruptive intent.
- Use an approved read-only equivalent where possible.
- Do not disable Safe mode without authorization and a documented reason.

### Device result is FAILED

- Read the specific error in the results table and Output pane.
- Separate device-specific failures from JumpServer failures.
- Retry only after correcting or understanding the cause.
- Record failed devices in the ticket.

## 11. Cancellation and Retry

**Cancel** stops queued work cooperatively. An SSH command already in progress may finish or wait for its configured timeout.

**Retry failed** reruns the previous command set only against unsuccessful or cancelled devices. Before retrying:

- Confirm the failure cause is temporary or corrected.
- Confirm the original scope is still valid.
- Confirm the commands are still appropriate.

## 12. Security and Data Handling

- Never share application passwords or device credentials in chat, tickets, or reports.
- Protect `%APPDATA%\ISPNetOpsTool\` and exported report folders.
- Do not copy the encryption key with exported reports.
- Do not commit credentials, host keys, inventory files, or reports to source control.
- Follow ISP retention and deletion requirements for operational evidence.
- Report unexpected SSH key changes immediately.

## 13. Ticket Evidence Template

Record the following in the ticket:

```text
Tool: ISP NetOps Tool
Operator: <operator>
Ticket/change: <reference>
Run time UTC: <timestamp>
JumpServer: <host or N/A>
Device scope: <device names or group>
Commands: <command list>
Successful devices: <count>
Failed devices: <count>
Export directory: <approved location>
Notes: <relevant findings and failures>
```

Attach the combined report and raw output only when permitted by the ticket’s data-handling policy.

## 14. Escalation

Escalate to the appropriate owner when:

- A router host key changes unexpectedly.
- Multiple devices fail through the same JumpServer.
- Authentication failures affect multiple accounts or sites.
- Output suggests a service-impacting condition.
- The tool produces inconsistent results across repeated runs.
- Local application data is corrupt.
- A command appears unsafe or outside the approved scope.

## 15. Change Control for This Manual

When the application gains a new capability, update this manual with:

1. The operator workflow.
2. Required permissions or prerequisites.
3. Expected output and evidence.
4. Failure and rollback handling.
5. Security and data-handling requirements.
6. Ticket documentation requirements.
