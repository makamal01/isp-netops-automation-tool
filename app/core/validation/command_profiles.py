from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandProfile:
    vendor: str
    platform: str
    protocol: str
    stage: str
    command_list: list[str]
    success_indicators: list[str]
    parse_rules: list[str]
    fallback_commands: list[str] = field(default_factory=list)
    notes: str = ""


DEFAULT_COMMAND_PROFILES: list[CommandProfile] = [
    CommandProfile(
        vendor="Cisco",
        platform="IOS-XR",
        protocol="IGP",
        stage="igp",
        command_list=[
            "show ospf neighbor",
            "show isis neighbors",
            "show ip route 10.0.0.2",
        ],
        success_indicators=["FULL", "Up", "Established", "Route present"],
        parse_rules=["neighbor_state", "route_presence"],
        notes=(
            "Cisco core verification profile for IGP readiness. Uses "
            "'show isis neighbors', not 'show isis adjacency' - the latter "
            "is '% Incomplete command' on IOS-XE (confirmed against live "
            "lab routers); 'neighbors' is supported across classic IOS, "
            "IOS-XE, and IOS-XR."
        ),
    ),
    CommandProfile(
        vendor="Cisco",
        platform="IOS-XR",
        protocol="MPLS",
        stage="mpls_signaling",
        command_list=[
            "show mpls ldp neighbor",
            "show mpls ldp bindings",
            "show mpls traffic-eng tunnels brief",
        ],
        success_indicators=["Operational", "Up", "Established"],
        parse_rules=["ldp_session", "lsp_state"],
        notes="Cisco MPLS signaling validation profile.",
    ),
    CommandProfile(
        vendor="Cisco",
        platform="IOS-XR",
        protocol="LSP",
        stage="lsp_transport",
        command_list=[
            "show mpls lsp",
            "show mpls forwarding-table",
            "show mpls traffic-eng tunnels summary",
        ],
        success_indicators=["Up", "Active", "label switched"],
        parse_rules=["lsp_state", "label_switching"],
        notes="Cisco LSP transport validation profile.",
    ),
    CommandProfile(
        vendor="Cisco",
        platform="IOS-XR",
        protocol="BGP",
        stage="bgp",
        command_list=[
            "show bgp summary",
            "show bgp ipv4 unicast summary",
            "show bgp neighbors",
        ],
        success_indicators=["Established", "Up", "Neighbor states"],
        parse_rules=["bgp_neighbor_state", "summary_status"],
        notes="Cisco BGP peer validation profile.",
    ),
    CommandProfile(
        vendor="Cisco",
        platform="IOS-XR",
        protocol="MP-BGP/VPN",
        stage="mp_bgp_vpn",
        command_list=[
            "show bgp vpnv4 unicast summary",
            "show route table vpnv4",
            "show vrf",
        ],
        success_indicators=["Established", "VPN", "Route present"],
        parse_rules=["vpn_route_presence", "mp_bgp_state"],
        notes="Cisco VPN/MP-BGP validation profile.",
    ),
    CommandProfile(
        vendor="Huawei",
        platform="VRP",
        protocol="IGP",
        stage="igp",
        command_list=[
            "display ospf peer",
            "display isis peer",
            "display ip routing-table 10.0.0.2",
        ],
        success_indicators=["Full", "Up", "Established", "Route present"],
        parse_rules=["neighbor_state", "route_presence"],
        notes="Huawei IGP validation profile.",
    ),
    CommandProfile(
        vendor="Huawei",
        platform="VRP",
        protocol="MPLS",
        stage="mpls_signaling",
        command_list=[
            "display mpls ldp peer",
            "display mpls ldp session",
            "display mpls lsp",
        ],
        success_indicators=["Operational", "Up", "Established"],
        parse_rules=["ldp_session", "lsp_state"],
        notes="Huawei MPLS signaling validation profile.",
    ),
    CommandProfile(
        vendor="Huawei",
        platform="VRP",
        protocol="LSP",
        stage="lsp_transport",
        command_list=[
            "display mpls lsp verbose",
            "display mpls tunnel-info",
            "display mpls forwarding-table",
        ],
        success_indicators=["Up", "Active", "Label switched"],
        parse_rules=["lsp_state", "label_switching"],
        notes="Huawei LSP validation profile.",
    ),
    CommandProfile(
        vendor="Huawei",
        platform="VRP",
        protocol="BGP",
        stage="bgp",
        command_list=[
            "display bgp peer",
            "display bgp ipv4 unicast summary",
            "display bgp vpnv4 all peer",
        ],
        success_indicators=["Established", "Up", "Peer"],
        parse_rules=["bgp_neighbor_state", "summary_status"],
        notes="Huawei BGP validation profile.",
    ),
    CommandProfile(
        vendor="Huawei",
        platform="VRP",
        protocol="MP-BGP/VPN",
        stage="mp_bgp_vpn",
        command_list=[
            "display bgp vpnv4 all routing-table",
            "display ip vpn-instance",
            "display current-configuration | section bgp",
        ],
        success_indicators=["VPN", "Established", "Route present"],
        parse_rules=["vpn_route_presence", "mp_bgp_state"],
        notes="Huawei VPN/MP-BGP validation profile.",
    ),
    CommandProfile(
        vendor="Nokia",
        platform="SR OS",
        protocol="IGP",
        stage="igp",
        command_list=[
            "show router ospf neighbor",
            "show router isis adjacency",
            "show router route-table 10.0.0.2",
        ],
        success_indicators=["Full", "Up", "Established"],
        parse_rules=["neighbor_state", "route_presence"],
        notes="Nokia IGP validation profile.",
    ),
    CommandProfile(
        vendor="Nokia",
        platform="SR OS",
        protocol="MPLS",
        stage="mpls_signaling",
        command_list=[
            "show router ldp session",
            "show router mpls lsp",
            "show router ldp peer",
        ],
        success_indicators=["Operational", "Up", "Established"],
        parse_rules=["ldp_session", "lsp_state"],
        notes="Nokia MPLS/transport validation profile.",
    ),
    CommandProfile(
        vendor="Nokia",
        platform="SR OS",
        protocol="LSP",
        stage="lsp_transport",
        command_list=[
            "show router mpls lsp detail",
            "show router mpls tunnel-table",
            "show router mpls interface",
        ],
        success_indicators=["Up", "Active", "Operational"],
        parse_rules=["lsp_state", "label_switching"],
        notes="Nokia LSP validation profile.",
    ),
    CommandProfile(
        vendor="Nokia",
        platform="SR OS",
        protocol="BGP",
        stage="bgp",
        command_list=[
            "show router bgp summary",
            "show router bgp neighbor",
            "show router route-table vpnv4",
        ],
        success_indicators=["Established", "Up", "Active"],
        parse_rules=["bgp_neighbor_state", "summary_status"],
        notes="Nokia BGP validation profile.",
    ),
    CommandProfile(
        vendor="Nokia",
        platform="SR OS",
        protocol="MP-BGP/VPN",
        stage="mp_bgp_vpn",
        command_list=[
            "show router bgp vpnv4 summary",
            "show router route-table vpnv4",
            "show service id 1 base",
        ],
        success_indicators=["Established", "VPN", "Route present"],
        parse_rules=["vpn_route_presence", "mp_bgp_state"],
        notes="Nokia VPN/MP-BGP validation profile.",
    ),
]


def _normalize_vendor(vendor: str) -> str:
    normalized = (vendor or "").strip().lower()
    aliases = {
        "cisco ios-xe": "cisco",
        "cisco ios xe": "cisco",
        "cisco ios": "cisco",
        "cisco": "cisco",
        "huawei vrp": "huawei",
        "huawei": "huawei",
        "nokia sr os": "nokia",
        "nokia": "nokia",
    }
    return aliases.get(normalized, normalized)


def _normalize_platform(platform: str) -> str:
    normalized = (platform or "").strip().lower()
    aliases = {
        # The MVP command matrix documents Cisco IOS-XR/XE checks together
        # (MPLS_VALIDATION_IMPLEMENTATION_PLAN.md #4/#13), and only IOS-XR
        # profiles are defined below, so IOS-XE is aliased onto them instead
        # of falling through the vendor-only fallback silently.
        "ios-xe": "ios-xr",
        "ios xe": "ios-xr",
        "ios-xr": "ios-xr",
        "ios xr": "ios-xr",
        "sr os": "sr os",
        "sros": "sr os",
        "vrp": "vrp",
        "huawei": "vrp",
    }
    return aliases.get(normalized, normalized)


def get_profiles_for(vendor: str, platform: str, stage: str | None = None) -> list[CommandProfile]:
    vendor_key = _normalize_vendor(vendor)
    platform_key = _normalize_platform(platform)

    profiles = [
        profile for profile in DEFAULT_COMMAND_PROFILES
        if _normalize_vendor(profile.vendor) == vendor_key and _normalize_platform(profile.platform) == platform_key
    ]

    if not profiles:
        profiles = [
            profile for profile in DEFAULT_COMMAND_PROFILES
            if _normalize_vendor(profile.vendor) == vendor_key
        ]

    if stage:
        profiles = [profile for profile in profiles if profile.stage == stage]

    if not profiles and vendor_key == "cisco":
        profiles = [
            profile for profile in DEFAULT_COMMAND_PROFILES
            if _normalize_vendor(profile.vendor) == "cisco"
        ]
        if stage:
            profiles = [profile for profile in profiles if profile.stage == stage]

    return profiles
