# Software Upgrade Suite — Parked Notes

**Status: parked (2026-09-28).** Captures the suggested direction so the work
can resume without redoing it. Phase 1 is a candidate for the small useful
(non-AI) version, since it is read-only.

## Idea

Pre-checks before a software upgrade, post-checks after it, and a guided
upgrade following the method of procedure (MOP) an experienced network
engineer would use.

## Why phased

The app's promise is read-only with safe mode on. An upgrade writes files,
changes boot images, and reloads live routers, so a bad one costs a customer.
Much of an upgrade project's value is proving before == after, and that part
is read-only. Build trust with the read-only phases first.

## Phase 1 — pre/post checks (read-only)

Reuses command profiles, TextFSM parsing, the validation layers, reports,
and the audit log.

1. **Pre-snapshot** per device:
   - version and uptime
   - hardware, environment, redundancy/standby state
   - interfaces (state, errors)
   - IGP adjacencies, LDP/RSVP sessions, LSPs
   - BGP neighbours and prefix counts per neighbour
   - VRF route counts
   - CPU, memory, storage
   - licences
   - recent logs
   - full config backup
2. **Post-snapshot**: the same set of commands.
3. **Rule-based comparison**, not a raw text diff:
   - exact match (all BGP sessions re-established)
   - tolerance (prefix count within ±N%)
   - expected change (uptime reset)
   - failure (new interface down)
4. **Verdict** (pass/warn/fail) with evidence, plus a report the engineer can
   attach to the change ticket.

The existing MPLS validation (IGP → MPLS → LSP → BGP → VPN) is already most of
a post-check.

## Phase 2 — upgrade-readiness checks (mostly read-only)

- Enough free storage for the image.
- Image present, and its checksum matches the vendor-published hash.
- Target release is on a maintained allowed list per platform (from vendor
  release notes, including required intermediate versions).
- Redundancy is healthy.
- Config backup taken.
- Change ticket number entered.
- Out-of-band console access confirmed by the operator.

## Phase 3 — guided execution (writes, heavily gated)

**Sequence:**
1. Readiness checks pass.
2. Drain traffic (BGP graceful shutdown; IS-IS overload bit / OSPF
   max-metric).
3. Set the boot image.
4. Save the config.
5. Reload.
6. Poll until the device is reachable again, with a timeout.
7. Post-checks.
8. Restore traffic.
9. Operator sign-off.

**Rules:**
- A human confirms each step.
- Each step has automatic stop conditions and a written rollback.
- Execution needs MFA re-authentication and deployment-policy approval
  (`requires_approval_for`).
- Never upgrade both halves of a redundant pair in the same wave.
- One device first, a soak period, then waves.
- Run state is saved and resumable.
- Everything is audit-logged.

Vendor mechanics (IOS-XE install mode, SR OS BOF, Huawei VRP startup
system-software, ISSU on dual-supervisor chassis) must come from each
platform's official procedure. Start with one vendor/platform, test it in the
EVE-NG lab, then expand.

## On "industry standards"

There is no single formal router-upgrade standard. Practice is vendor
upgrade procedures and release notes, plus ITIL-style change management
(ticket, approval, window, rollback), plus the MOP / pre-check / post-check
discipline. Market it as "vendor-procedure-driven, change-managed upgrades".

## Business angle

- Phase 1 sells on its own (evidence-backed pre/post reports).
- Phase 3 is premium and needs liability terms in the contract.
- Pairs later with the parked AI assistant (explaining failed comparisons);
  see `AI_ASSISTANT_PARKED_NOTES.md`.

## Open question when resuming

Which vendor and platform to support first? The lab has IOS-XE and SR OS.
