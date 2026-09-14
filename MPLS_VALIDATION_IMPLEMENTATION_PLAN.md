# MPLS Validation Implementation Plan

## 1. Goal

Implement the first production-ready version of the Layered MPLS / VPN Validation feature as a guided, dependency-aware troubleshooting workflow.

This version will:

- validate one layer at a time
- validate the full chain in the correct order
- enforce vendor-aware command profiles
- present clear evidence and final root-cause guidance
- avoid free-text command entry in the main workflow
- leave AI as a later optional phase

---

## 2. Product Scope for MVP

### In scope

- IGP validation
- MPLS signaling validation
- LSP / transport validation
- BGP validation
- MP-BGP / VPN validation
- vendor-specific command library
- stage-by-stage dependency logic
- pass/fail/unknown status reporting
- evidence capture
- overall path summary

### Out of scope for MVP

- freeform raw CLI commands as default workflow
- AI-generated command selection
- autonomous remediation
- deep statistical analytics
- full EVPN / SRv6 complexity
- every vendor and every platform variation in v1

---

## 3. Architectural Principle

The system must be structured around an explicit validation engine rather than ad hoc commands.

The desired flow is:

1. User enters path context
2. System loads vendor profile
3. System runs the correct command set for the chosen stage
4. System normalizes the output into a stage result
5. The engine decides whether to continue or stop based on dependency rules
6. System returns a human-readable path verdict

---

## 4. Validation Stages

### Stage 1: IGP

Purpose:
- confirm the control-plane core path is healthy

Checks:
- OSPF neighbor status
- IS-IS adjacency
- loopback / peer reachability
- route presence toward remote node

Example command families:

Cisco IOS-XR / XE
- show ospf neighbor
- show isis adjacency
- show ip route <peer>

Huawei VRP
- display ospf peer
- display isis peer
- display ip routing-table <peer>

Nokia SR OS
- show router ospf neighbor
- show router isis adjacency
- show router route-table <prefix>

Success criteria:
- neighbor is up / established
- route to peer is present
- no adjacency down states

Failure logic:
- stop the validation flow
- explain that lower-layer IGP failure prevents MPLS/BGP validation from being meaningful

---

### Stage 2: MPLS Signaling

Purpose:
- confirm MPLS control-plane neighbors are formed

Checks:
- LDP neighbor status
- MPLS neighbor establishment
- RSVP-TE or SR-TE signaling status where applicable

Cisco IOS-XR / XE
- show mpls ldp neighbor
- show mpls traffic-eng tunnels brief
- show segment-routing policy

Huawei VRP
- display mpls ldp peer
- display mpls lsp
- display current-configuration section mpls

Nokia SR OS
- show router ldp session
- show router mpls lsp
- show router rsvp session

Success criteria:
- LDP neighbor is operational / established
- MPLS LSP or tunnel is active where expected
- no signaled path failure

Failure logic:
- stop or warn before BGP validation
- root-cause likely lies in label transport establishment

---

### Stage 3: LSP / Transport Validation

Purpose:
- confirm the actual transport label path is up

Checks:
- LSP present and active
- label forwarding behavior
- RSVP-TE / SR-TE path health

Cisco IOS-XR
- show mpls ldp bindings
- show mpls forwarding
- show mpls traffic-eng tunnels

Huawei
- display mpls lsp
- display mpls forwarding-table

Nokia
- show router mpls lsp detail
- show router mpls forwarding

Success criteria:
- label path exists
- forwarding state is active
- path is not down / failed / stale

Failure logic:
- on failure, report transport issue before BGP and VPN validation proceeds

---

### Stage 4: BGP Validation

Purpose:
- verify routing adjacency to the required neighbor

Checks:
- BGP summary
- peer state
- route exchange presence

Cisco IOS-XR / XE
- show bgp summary
- show bgp vpnv4 unicast summary
- show bgp neighbor <peer>

Huawei
- display bgp peer
- display bgp vpnv4 vpn-instance <vrf> peer

Nokia
- show router bgp summary
- show router bgp neighbor
- show router bgp vpn-ipv4 summary

Success criteria:
- neighbor state established
- route exchange is active
- expected prefixes are learned

Failure logic:
- stop before MP-BGP / VPN validation if BGP is not established

---

### Stage 5: MP-BGP / VPN Validation

Purpose:
- verify the VPN route family and route-target interchange

Checks:
- VPNv4 / VPNv6 summary
- route-target import/export validity
- VRF route table presence

Cisco IOS-XR / XE
- show bgp vpnv4 unicast summary
- show route table <vrf>
- show route-target

Huawei
- display bgp vpnv4 vpn-instance <vrf> routing-table
- display ip routing-table vpn-instance <vrf>

Nokia
- show router bgp vpn-ipv4 summary
- show router route-table vpn <vrf>

Success criteria:
- VPN routes are visible
- route target import/export is correct
- route is available in the intended VRF

Failure logic:
- classify as service-policy or VPN route issue, not transport issue

---

## 5. Dependency Matrix

| Stage | Depends On | If Fails | Result |
|---|---|---|---|
| IGP | none | stop | Lower-layer core issue |
| MPLS signaling | IGP | stop | LDP / RSVP / SR-TE problem |
| LSP / transport | IGP + MPLS signaling | stop | forwarding path issue |
| BGP | IGP + transport | stop | neighbor or route exchange issue |
| MP-BGP / VPN | IGP + transport + BGP | stop | route policy / VRF issue |
| Final service | all above | report | service-specific failure |

---

## 6. Command Library Design

### Command profile format

Each protocol stage will include a vendor-aware command profile object.

```python
@dataclass
class CommandProfile:
    vendor: str
    platform: str
    protocol: str
    stage: str
    command_list: list[str]
    success_indicators: list[str]
    parse_rules: list[str]
    fallback_commands: list[str] = None
```

### Example profile entries

```python
CommandProfile(
    vendor="Cisco",
    platform="IOS-XR",
    protocol="IGP",
    stage="igp",
    command_list=[
        "show ospf neighbor",
        "show ip route 10.0.0.2",
        "show isis adjacency"
    ],
    success_indicators=["FULL", "UP", "Established", "Route present"],
    parse_rules=["neighbor_state", "route_presence"],
)
```

```python
CommandProfile(
    vendor="Nokia",
    platform="SR OS",
    protocol="MPLS",
    stage="mpls_signaling",
    command_list=[
        "show router ldp session",
        "show router mpls lsp"
    ],
    success_indicators=["Operational", "Up", "Established"],
    parse_rules=["ldp_session", "lsp_state"],
)
```

---

## 7. Normalized Result Model

### Result structure

```python
@dataclass
class StageResult:
    stage: str
    status: str  # passed, failed, degraded, unknown
    vendor: str
    platform: str
    commands: list[str]
    raw_output: str
    parsed_summary: dict
    evidence: list[str]
    next_step: str
    confidence: str
```

### Final path result

```python
@dataclass
class ValidationResult:
    overall_status: str
    failed_stage: str | None
    stage_results: list[StageResult]
    root_cause: str
    recommendation: str
    summary: str
```

---

## 8. Parsing Strategy

Parsing should be vendor-aware and output-driven.

### Parse categories

- neighbor_state
- route_presence
- ldp_session_state
- lsp_state
- bgp_state
- vpn_route_presence
- vrf_route_target_match

### Parsing rules

- The system should parse only target states, not entire logs
- Use regex and keyword checks for expected status values
- Normalize output into a common internal state model
- Store raw output for audit purposes
- Display both raw and interpreted output to the user

---

## 9. Dependency Engine Logic

### Pseudocode

```python
stages = ["igp", "mpls_signaling", "lsp_transport", "bgp", "mp_bgp_vpn"]

for stage in stages:
    result = run_stage(stage)
    if result.status == "failed":
        return ValidationResult(
            overall_status="failed",
            failed_stage=stage,
            stage_results=results,
            root_cause=derive_root_cause(stage),
            recommendation=derive_recommendation(stage),
            summary=build_summary(results)
        )

return ValidationResult(
    overall_status="passed",
    failed_stage=None,
    stage_results=results,
    root_cause="None detected",
    recommendation="Proceed with service validation.",
    summary=build_summary(results)
)
```

### Dependency notes

- IGP must pass before MPLS signaling is considered valid
- MPLS must be valid before BGP and VPN checks are considered meaningful
- BGP must be valid before VPN route policy is meaningful
- Final service result should reflect the deepest failing stage

---

## 10. UI Flow

### Dashboard layout

1. Path context panel
   - Side A IP / device
   - Side B IP / device
   - Vendor
   - Platform
   - Service type
   - Mode: single stage or full chain

2. Validation actions
   - Run selected stage
   - Run full chain
   - Export evidence
   - Save report

3. Stage results panel
   - IGP status
   - MPLS status
   - BGP status
   - VPN status
   - final summary

4. Evidence panel
   - raw command output
   - normalized interpretation
   - recommended next steps

### UX principles

- clear stage-by-stage progress
- no raw command entry in default workflow
- no confusion between raw logs and interpreted status
- strong action guidance after failure

---

## 11. Test Strategy

### Unit tests

- command profile loading
- stage ordering logic
- dependency-stop conditions
- parser behavior for vendor output samples
- result normalization

### Integration tests

- run a sample Cisco template against mocked output
- run a sample Nokia template against mocked output
- run a full chain where IGP fails and ensure BGP is not evaluated further
- run a full chain where all stages pass and ensure overall status is passed

### Regression tests

- unsupported vendor/platform profile handling
- fallback command selection
- unknown command detection
- output parsing edge cases

---

## 12. Implementation Plan by Layer

### Phase 1: Core validation engine

Create core modules:

- `app/core/validation/validation_engine.py`
- `app/core/validation/command_profiles.py`
- `app/core/validation/protocol_matrix.py`
- `app/core/validation/parsers.py`
- `app/core/validation/models.py`

### Phase 2: UI integration

Add:

- new validation dialog or panel in the GUI
- inputs for path context
- stage status cards
- evidence pane
- final summary area

### Phase 3: Report generation

- save validation results in a readable report
- include stage output and recommendations
- export to text or CSV

### Phase 4: Additional vendor coverage

- add more profiles for Juniper
- expand Nokia/Huawei coverage
- include SR-TE / EVPN variant checks later

---

## 13. MVP Command Matrix

### Cisco

IGP
- show ospf neighbor
- show isis adjacency
- show ip route <peer>

MPLS
- show mpls ldp neighbor
- show mpls lsp
- show mpls traffic-eng tunnels

BGP
- show bgp summary
- show bgp vpnv4 unicast summary

VPN / VRF
- show route table <vrf>
- show route-target

### Huawei

IGP
- display ospf peer
- display isis peer
- display ip routing-table <peer>

MPLS
- display mpls ldp peer
- display mpls lsp

BGP
- display bgp peer
- display bgp vpnv4 vpn-instance <vrf> peer

VPN / VRF
- display ip routing-table vpn-instance <vrf>

### Nokia

IGP
- show router ospf neighbor
- show router isis adjacency
- show router route-table <prefix>

MPLS
- show router ldp session
- show router mpls lsp
- show router rsvp session

BGP
- show router bgp summary
- show router bgp neighbor

VPN / VRF
- show router bgp vpn-ipv4 summary
- show router route-table vpn <vrf>

---

## 14. Data and Reporting Requirements

The system should save:

- validation request metadata
- selected vendor and platform
- full stage results
- raw command output
- normalized summaries
- final root cause explanation
- final recommendation
- timestamp and operator identity if available

This provides useful auditability for troubleshooting follow-up.

---

## 15. Risks and Mitigations

### Risk: command differences across releases
Mitigation:
- maintain release-aware profiles
- include fallback command variants
- explicitly mark unsupported operations

### Risk: operator tries to bypass the system
Mitigation:
- keep default workflow guided and restricted
- advanced raw-command mode should be optional and clearly labeled

### Risk: false positives in parser logic
Mitigation:
- require evidence-based states
- flags for ambiguous output
- normalize only supported status values

### Risk: unsupported feature combinations
Mitigation:
- UI should disable unsupported stages per vendor/platform
- route policy and VRF checks should require service type information

---

## 16. Recommended First Release

### Deliverables for v1

- guided path validation dashboard
- stage-by-stage validation engine
- profile library for Cisco / Huawei / Nokia
- full chain execution for MPLS core path validation
- evidence and recommendation panel

### Non-goals for v1

- AI summarization
- advanced topology mapping
- generic arbitrary CLI execution
- full Juniper coverage

---

## 17. Summary

This implementation pattern is the correct fit for the project because it avoids operator memory dependence, enforces sequential logic, and aligns with real ISP troubleshooting behavior.

The product will be strong because it:

- validates the lower layers before the service layer
- standardizes command usage across NOC engineers
- produces clear evidence and root-cause guidance
- is safe for junior users
- can evolve without forcing AI into the system core

---

## 18. Immediate Next Action

The next steps are:

1. define the exact first-release command profiles for Cisco / Huawei / Nokia
2. implement the validation engine model classes
3. create the GUI flow for single-stage and full-chain validation
4. add test fixtures for each stage

Once those are in place, we can begin the actual code implementation in the app.
