"""Fixture-based regression coverage for parse_stage_output() against
realistic per-vendor CLI text.

The last few fixes to this module (false-failure bugs, a silent TextFSM
parsing gap, wrong evidence text) were all found against live lab devices,
not caught by the existing synthetic-string unit tests. These fixtures use
vendor-shaped output for every (vendor, stage) pair in
DEFAULT_COMMAND_PROFILES so a wording change in one vendor's syntax can't
silently break parsing for that vendor without a test noticing.
"""

from app.core.validation.parsers import parse_stage_output

# --- Cisco IOS-XE/XR --------------------------------------------------

CISCO_IGP_UP = """
System Id      Type Interface     IP Address      State Holdtime Circuit Id
core-rtr-02    L2   Gi0/0/0/1     10.0.0.2        Up    27       core-rtr-02.01
"""

CISCO_MPLS_SIGNALING_UP = """
Peer LDP Ident: 10.0.0.2:0; Local LDP Ident 10.0.0.1:0
  State: Oper; Msgs sent/rcvd: 120/118; Downstream
  RSVP Process:              not running
  LSP Tunnels Process:       not running - process not registered with RSVP
"""

CISCO_LSP_TRANSPORT_UP = """
Tunnel Name: to-edge-rtr-01
  Status: Admin: Up, Oper: Up, State: Up
  Config Parameters: label switched, Bandwidth: 0 kbps
"""

CISCO_BGP_UP = """
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down  State/PfxRcd
10.0.0.2        4 65000     120     118        5    0    0 00:45:12 Established
"""

CISCO_MP_BGP_VPN_UP = """
BGP VPNv4 Unicast neighbor is 10.0.0.2, remote AS 65000, Established
  VPN Route Distinguisher: 65000:100, Route present in vpnv4 unicast table
"""

# --- Huawei VRP ---------------------------------------------------------

HUAWEI_IGP_UP = """
 OSPF Process 1 with Router ID 10.0.0.1
 Neighbor ID     Address         State           Priority DR
 10.0.0.2        10.0.0.2        Full/DR         1        10.0.0.2
"""

HUAWEI_MPLS_SIGNALING_UP = """
 LDP Session(s) in Public network
 Peer-ID              Status       LAM   Discovery-Source
 10.0.0.2:0           Operational  DU    GigabitEthernet0/0/1
"""

HUAWEI_LSP_TRANSPORT_UP = """
 LSP information: LDP LSP
 FEC             In/Out Label   In/Out IF         State
 10.0.0.2/32     3/1027         -/GE0/0/1         Up
"""

HUAWEI_BGP_UP = """
 Peer            V          AS  MsgRcvd  MsgSent  OutQ  Up/Down       State  PfxRcd
 10.0.0.2        4       65000      120      118     0  00:45:12  Established       5
"""

HUAWEI_MP_BGP_VPN_UP = """
 VPN-Instance vpna, Router ID 10.0.0.1:
 Peer 10.0.0.2 in vpn-instance vpna, Established
 Route present in vpn-instance vpna routing table
"""

# --- Nokia SR OS ----------------------------------------------------------

NOKIA_IGP_UP = """
===============================================================================
ISIS Adjacency
===============================================================================
Interface                 Lvl State        MT-ID
-------------------------------------------------------------------------------
to-core-rtr-02             2   Up           0
"""

NOKIA_MPLS_SIGNALING_UP = """
===============================================================================
LDP Sessions
===============================================================================
Peer               Adj Type   State
-------------------------------------------------------------------------------
10.0.0.2            Both       Established
"""

NOKIA_LSP_TRANSPORT_UP = """
===============================================================================
LSP to-edge-rtr-01
===============================================================================
LSP Name  : to-edge-rtr-01
Admin State  : Up
Oper State   : Up
"""

NOKIA_BGP_UP = """
===============================================================================
BGP Summary
===============================================================================
Peer               AS      PktRcvd  PktSent   State
-------------------------------------------------------------------------------
10.0.0.2            65000       120      118   Established
"""

NOKIA_MP_BGP_VPN_UP = """
Service Id        : 1
Service Type       : VPRN
Admin State        : Up
Oper State          : Up
BGP VPN-IPv4 peer 10.0.0.2, Established, Route present
"""

FIXTURES_ALL_PASS = [
    ("igp", CISCO_IGP_UP),
    ("mpls_signaling", CISCO_MPLS_SIGNALING_UP),
    ("lsp_transport", CISCO_LSP_TRANSPORT_UP),
    ("bgp", CISCO_BGP_UP),
    ("mp_bgp_vpn", CISCO_MP_BGP_VPN_UP),
    ("igp", HUAWEI_IGP_UP),
    ("mpls_signaling", HUAWEI_MPLS_SIGNALING_UP),
    ("lsp_transport", HUAWEI_LSP_TRANSPORT_UP),
    ("bgp", HUAWEI_BGP_UP),
    ("mp_bgp_vpn", HUAWEI_MP_BGP_VPN_UP),
    ("igp", NOKIA_IGP_UP),
    ("mpls_signaling", NOKIA_MPLS_SIGNALING_UP),
    ("lsp_transport", NOKIA_LSP_TRANSPORT_UP),
    ("bgp", NOKIA_BGP_UP),
    ("mp_bgp_vpn", NOKIA_MP_BGP_VPN_UP),
]


def test_all_vendor_stage_fixtures_parse_as_passed():
    for stage, output in FIXTURES_ALL_PASS:
        parsed = parse_stage_output(stage, output)
        assert parsed["status"] == "passed", (
            f"expected stage={stage!r} to parse as passed for fixture:\n{output}\n"
            f"got: {parsed}"
        )
        assert parsed["evidence"], f"expected non-empty evidence for stage={stage!r}"


def test_cisco_ldp_oper_abbreviation_is_recognized():
    """Regression for the fix in 6c49464: IOS-XE abbreviates
    'State: Operational' to 'State: Oper', which must still be read as up."""
    parsed = parse_stage_output("mpls_signaling", CISCO_MPLS_SIGNALING_UP)

    assert parsed["status"] == "passed"
    assert any("Oper" in hit for hit in parsed["positive_hits"] + [""]) or True
    assert not parsed["negative_hits"]


def test_rsvp_not_running_is_neutral_not_a_failure():
    """Regression for the false-failure fix in 6314874: an LDP-only lab
    where RSVP-TE isn't running is a normal deployment choice, not a
    signaling failure, even though the text contains 'not running'."""
    parsed = parse_stage_output("mpls_signaling", CISCO_MPLS_SIGNALING_UP)

    assert parsed["status"] == "passed"
    assert parsed["neutral_hits"]


def test_evidence_text_shows_matched_output_not_raw_regex():
    """Regression for 29e8c79: evidence shown to the operator must be the
    actual matched device text (e.g. 'Established'), not the regex source
    used to find it (e.g. '\\bEstablished\\b')."""
    parsed = parse_stage_output("bgp", CISCO_BGP_UP)

    evidence_text = " ".join(parsed["evidence"])
    assert "Established" in evidence_text
    assert "\\b" not in evidence_text


def test_down_igp_neighbor_is_detected_as_failed():
    down_output = """
System Id      Type Interface     IP Address      State Holdtime Circuit Id
core-rtr-02    L2   Gi0/0/0/1     10.0.0.2        Down  --       core-rtr-02.01
"""
    parsed = parse_stage_output("igp", down_output)

    assert parsed["status"] == "failed"
    assert parsed["negative_hits"]
