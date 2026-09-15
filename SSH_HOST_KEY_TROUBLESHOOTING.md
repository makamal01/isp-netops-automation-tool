# SSH Host-Key Troubleshooting (Cisco / Huawei / Nokia / JumpServer)

Personal runbook for the "host key changed" failure in the ISP NetOps Tool's
lab (EVE-NG). Not a security bypass guide - it's the same "obtain and verify
the key through an approved channel" procedure the app's own
[DEVELOPER_TECHNICAL_GUIDE.md](DEVELOPER_TECHNICAL_GUIDE.md) requires, just
with the exact commands filled in and confirmed live against this lab.

## When you need this

The app raises one of these from a device or the JumpServer:

- `Host key for server '<ip>' does not match: got '<key>', expected '<key>'`
  -> the stored key is **stale/wrong** (most common cause here: EVE-NG lab
  nodes get a fresh SSH host key whenever they're rebuilt). This is what hit
  `10.246.111.1`/`10.246.111.2` on 2026-09-14.
- `Server '<ip>' not found in known_hosts` -> the host has **no** stored key
  yet (first time connecting to it).

Both are fixed the same way: get the device's real current key, then write
it into the app's trust store.

The app's trust store is a plain OpenSSH-format `known_hosts` file at:

```
%APPDATA%\ISPNetOpsTool\known_hosts
```

One line per host: `<ip> <key-type> <base64-key>`. To fix a mismatch,
replace that host's existing line; to fix "not found", add a new line.

## Step 1: get the device's real current key

**This machine can only reach the JumpServer (192.168.1.104) directly** -
the lab routers (10.246.222.x, 10.246.111.x) are only reachable *through*
it. So the scan has to run *from* the jump host, not from this Windows box.

This one method is vendor-agnostic and is what actually fixed the Nokia
issue - confirmed working against both Cisco IOS-XE and Nokia SR OS in this
lab, and it'll work the same way for Huawei VRP (it's just SSH protocol
negotiation, not vendor CLI):

```bash
# from a shell that can reach the jump host (or via paramiko exec_command
# through it, same as the app does) - run keyscan ON the jump host:
ssh -o StrictHostKeyChecking=accept-new devopsengineer@192.168.1.104 \
  "ssh-keyscan -T 5 -t rsa,ed25519,ecdsa <router-ip>"
```

That prints a ready-to-use `known_hosts` line, e.g.:
```
10.246.111.1 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB...
```

If the JumpServer's *own* key is the one that changed, scan it directly
from this machine instead (it's directly reachable):
```bash
ssh-keyscan -T 5 -t rsa,ed25519,ecdsa 192.168.1.104
```

## Step 2: cross-check on the device itself (optional but recommended)

Scanning over the network and reading the key from the device's own CLI are
two independent channels - if they agree, you're not looking at a
man-in-the-middle. Live-tested commands, keep for reference:

**Cisco IOS / IOS-XE** - confirmed against POC1-1/POC1-2:
```
show crypto key mypubkey rsa
```
Prints the router's RSA key pairs as raw hex (not a short fingerprint), so
it's a "yes a key exists and was regenerated at time X" check rather than a
quick byte-for-byte compare against `ssh-keyscan` output.

**Nokia SR OS** - confirmed against POC1-1_Nokia/POC1-2_Nokia, and this one
*is* directly comparable - it prints a clean fingerprint:
```
show system security ssh
```
Look for `RSA Host Key Fingerprint` / `DSA Host Key Fingerprint` in the
output.

**Huawei VRP** - not verified live (no Huawei device in this lab yet); this
is the documented VRP equivalent, treat it as reference until confirmed
against a real box:
```
display rsa local-key-pair public
```

## Step 3: update the app's known_hosts file

Edit `%APPDATA%\ISPNetOpsTool\known_hosts`:
- **Mismatch**: find the line starting with that IP and replace the
  `<key-type> <base64-key>` portion with the freshly scanned one.
- **Not found**: add the scanned line as a new line in the file.

Then retry the connection in the app (or re-run the same bulk/validation
job) - no restart needed, the file is read fresh per run.

## Step 4: verify

Run a harmless read-only command (`show version` / `display version`)
against just the affected device(s) and confirm it actually returns real
output, not just "no error." A silent connect with empty output can still
mean something else is wrong.

## Don't do this in production

This lab-only shortcut (trust whatever the jump host currently sees) is
fine here because it's a disposable EVE-NG lab where node rebuilds are the
expected cause. On real ISP infrastructure, an unexpected host-key change is
a genuine security event - stop and verify the new key through an
out-of-band channel (call the site, check a change ticket, compare against
a config-management record) before trusting it, per the app's documented
policy in DEVELOPER_TECHNICAL_GUIDE.md's Host-key verification section.
