# MPLS Path Validation Product Spec

## 1. Overview

This feature adds a layered troubleshooting dashboard to the ISP NetOps Tool that validates MPLS and VPN readiness between two nodes in a dependency-aware flow.

The product goal is not to allow arbitrary command entry as the default workflow. Instead, it must use a curated vendor-aware command library and enforce a known-good validation sequence so a NOC engineer can reliably answer:

- Is the IGP up between A and B?
- Is MPLS signaling established?
- Is the LSP / transport path available?
- Is BGP or MP-BGP established?
- Is the VPN / VRF service healthy?
- Where did the path fail?

This is designed for ISP operational use, especially where service activation and fault isolation depend on lower-layer MPLS health before MPLS VPN or BGP validation becomes meaningful.

---

## 2. Core Product Principle

The system must follow a layered dependency model, not a simple protocol-by-protocol checklist without context.

Valid order:

1. IGP
2. MPLS signaling / label transport
3. LSP / RSVP-TE / SR-TE path validation
4. BGP / MP-BGP
5. VPN / VRF route policy and route exchange
6. Final service readiness status

If the lower layer is down, the tool should stop and explain why downstream checks are not meaningful.

---

## 3. Business Value to an ISP

This feature is operationally valuable because it:

- reduces MTTR (mean time to repair)
- standardizes troubleshooting across engineers
- reduces error risk from manual command recall
- improves service activation validation
- gives consistent evidence for escalations and audits
- helps junior NOC engineers follow the correct workflow
- reduces false conclusions such as blaming BGP when the IGP or MPLS stack is actually broken

---

## 4. Primary Use Cases

### 4.1 Single Protocol Validation
A user wants to check one layer only, such as:

- OSPF / IS-IS adjacency
- LDP neighbor establishment
- MPLS LSP state
- BGP summary
- MP-BGP status
- VRF / VPN route target health

### 4.2 Full Chain Validation
A user wants to validate the service path end-to-end:

- side A IP / hostname
- side B IP / hostname
- expected service type
- vendor and platform
- click Validate Path

The system then runs the dependency chain in order and returns a final result.

### 4.3 Guided Troubleshooting
A user is not sure where the issue lies. The tool walks them through the layers and shows where the failure occurred.

---

## 5. Product Requirements

### 5.1 Functional Requirements

The system shall:

- allow a user to select a protocol layer or execute a full validation chain
- enforce vendor-specific command profiles
- use a dependency-order validation flow
- display pass / fail / degraded / unknown per stage
- show both raw output and normalized result data
- explain the likely root cause and next recommended validation step
- stop downstream checks if a prerequisite layer fails
- support multiple vendors and platform families

### 5.2 Non-Functional Requirements

The system shall:

- be safe and repeatable for NOC use
- minimize operator command knowledge requirements
- support audit logging
- be version-aware where possible
- present clear evidence for each result
- avoid arbitrary command execution in the primary workflow

---

## 6. Core User Experience

### 6.1 Main Inputs

The validation dashboard will require:

- Side A identifier (IP or device name)
- Side B identifier (IP or device name)
- vendor
- platform / OS family
- service type
- path type (generic MPLS, L3VPN, L2VPN, EVPN, etc.)
- optional VRF / route target / customer name

### 6.2 Modes

#### Mode 1: Layer-by-Layer
User selects one check type:

- IGP
- MPLS signaling
- LSP path
- BGP
- MP-BGP
- VPN / VRF

#### Mode 2: Full Path Validation
User runs the entire chain and gets a summary.

#### Mode 3: Advanced Validation
User can inspect deeper output or override results, but this is clearly marked as advanced use.

---

## 7. Data Model

### 7.1 Validation Request

```json
{
  "side_a": "10.0.0.1",
  "side_b": "10.0.0.2",
  "vendor": "Cisco",
  "platform": "IOS-XR",
  "service_type": "L3VPN",
  "path_type": "mpls_vpn",
  "vrf": "CUSTOMER-1",
  "mode": "full_chain",
  "protocol_focus": null
}
```

### 7.2 Stage Result

```json
{
  "stage": "igp",
  "status": "passed",
  "commands": [
    "show ospf neighbor",
    "show ip route 10.0.0.2"
  ],
  "evidence": [
    "Neighbor full/DR",
    "Route installed"
  ],
  "next_step": "Proceed to MPLS signaling validation",
  "confidence": "high"
}
```

### 7.3 Final Result

```json
{
  "overall_status": "failed",
  "failed_stage": "mpls_transport",
  "reason": "LDP neighbors are not established between the core nodes.",
  "recommended_action": "Verify core interfaces and MPLS enablement before checking BGP/VRF status.",
  "evidence_summary": [
    "IGP passed",
    "LDP failed",
    "BGP not evaluated because transport prerequisite failed"
  ]
}
```

---

## 8. Command Library Strategy

The system shall use a curated, versioned command library rather than free-text inputs for critical validation checks.

### 8.1 Command Profile Structure

Each command profile shall include:

- vendor
- platform
- OS family or release range
- protocol
- intended check
- command list
- parser rules
- expected success indicators
- alternative commands for compatibility
- notes or warnings for unsupported syntax

### 8.2 Security and Safety

The main flow must not require raw CLI typing. This is especially important for:

- junior engineers
- standardization across teams
- reducing configuration mistakes
- avoiding “wrong command, wrong interpretation” failures

### 8.3 Version Awareness

The system must handle output and syntax differences across releases. A profile should include:

- command variants by release
- fallback options
- compatibility logic
- unsupported command treatment

This ensures output remains trustworthy even when product releases differ.

---

## 9. Vendor Coverage

### Phase 1 Supported Vendors

- Cisco IOS-XE / IOS-XR
- Huawei VRP
- Nokia SR OS

These are the most relevant vendors for a typical ISP/MPLS deployment and align with the current project direction.

### Phase 2 Future Vendors

- Juniper Junos
- Cisco NX-OS (if applicable to service path checks)
- SR Linux variants

---

## 10. Protocol Group Coverage

### 10.1 IGP

Examples:

- OSPF neighbor state
- IS-IS adjacency
- loopback reachability
- route to remote peer

### 10.2 MPLS Signaling

Examples:

- LDP neighbor status
- RSVP-TE signaling state
- SR-TE policy status
- MPLS label distribution

### 10.3 LSP / Transport Validation

Examples:

- LSP up/down state
- ingress/egress label path viability
- tunnel existence and statistics

### 10.4 BGP / MP-BGP

Examples:

- BGP summary
- neighbor state
- route exchange
- VPNv4 / VPNv6 route presence

### 10.5 VPN / VRF

Examples:

- VRF instance status
- route-target import/export
- route table validation
- customer service route presence

---

## 11. Dependency Logic Design

The system must interpret the result in a dependency-aware way.

### Rule Set

- If IGP fails, stop and report a lower-layer issue.
- If MPLS signaling fails, do not claim BGP is healthy.
- If LSP is not established, BGP and VPN checks are not meaningful until transport is valid.
- If BGP is down, route-target or VRF checks cannot be treated as root cause without verifying the BGP layer first.

This means the final health result is not just “all checks pass/fail”; it is also “cause is likely in layer X.”

---

## 12. Result Interpretation Logic

Each stage should normalize command output into a standard interpretation.

Examples:

- neighbor state = Full / Up / Established
- LDP session = Operational / BGP route distribution = Established
- LSP = Up / Active
- VRF route target = Imported / Exported / Not present

The system should show:

- raw output
- parsed state
- business interpretation
- recommended next action

---

## 13. Error Prevention Strategy

This is a critical operational requirement.

### The product must prevent the following mistakes:

- user enters a wrong command
- user chooses incorrect vendor profile
- user runs BGP checks before MPLS checks
- user assumes route exchange is good when transport is down
- user relies on memory instead of validated command lists
- user misinterprets old syntax from another platform

### Prevention mechanisms

- fixed command profiles
- dropdowns instead of free-form command entry for standard flows
- compatibility logic by vendor/platform
- sequential stage gates
- evidence-based status reporting
- explicit “unsupported command for this platform” handling

---

## 14. AI Strategy

AI is intentionally excluded from the core control path. It is not the authority for command selection or state validation.

### AI later phase, optional

AI can be added later for:

- summarizing results in plain English
- explaining ambiguous output
- recommending next checks
- generating escalation notes or ticket content
- building a natural-language troubleshooting assistant

### AI should not be used for:

- deciding the command set for production validation
- claiming routing state without evidence
- bypassing vendor-specific validation logic
- generating the root cause without checking parser output

This keeps the tool operationally trustworthy.

---

## 15. MVP Scope

### Phase 1: Minimum Viable Product

Must include:

- Stage-based validation engine
- IGP validation
- MPLS / LDP / LSP validation
- BGP validation
- MP-BGP / VPN validation
- vendor-aware command library
- pass/fail/unknown status reporting
- evidence panel
- activity log
- full-path validation mode

### Phase 2: Production Hardening

- better vendor support
- command compatibility matrix
- historical result snapshots
- saved validation profiles
- route-target / VRF details
- cleaner operator workflows

### Phase 3: Advanced Features

- smarter dependency reasoning
- advanced reporting
- escalation templates
- AI-assisted summaries (optional later)

---

## 16. Acceptance Criteria

The feature is considered successful when:

1. A non-expert NOC engineer can validate a protocol layer without typing raw commands.
2. The system enforces the correct vendor-specific command profile.
3. Lower-layer failures stop downstream checks automatically.
4. Results include clear evidence and interpretation.
5. The tool supports at least Cisco, Huawei, and Nokia MPLS validation flows.
6. A user can perform either single-layer validation or full-path validation.
7. The tool reduces guesswork and improves troubleshooting consistency.

---

## 17. Recommended Design Summary

The recommended product is a Layered MPLS / VPN Validation Dashboard built around:

- fixed command libraries
- vendor-aware validation profiles
- dependency-chain execution
- clear pass/fail evidence
- standardized NOC troubleshooting workflow
- AI postponed to a later optional phase

This gives the project a safe, reliable, and scalable path forward.

---

## 18. Immediate Next Step

The next engineering task should be to define the initial protocol matrix and command profile templates for the first release:

- IGP checks
- MPLS signaling checks
- LSP checks
- BGP checks
- MP-BGP / VPN checks
- vendor mapping for Cisco / Huawei / Nokia

Once this matrix is defined, the app can be structured around that command library and the dependency engine can be implemented on top of it.
