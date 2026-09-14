from __future__ import annotations

import re
from typing import Any


_STAGE_PATTERNS = {
    "igp": {
        "positive": [
            r"FULL",
            r"2-WAY",
            r"Up",
            r"Established",
            r"Reachable",
            r"Neighbor is up",
            r"Adjacency.*up",
            r"route.*present",
        ],
        "negative": [
            r"DOWN",
            r"INIT",
            r"DOWN\s*\|",
            r"No route",
            r"not found",
            r"Inactive",
            r"not established",
        ],
    },
    "mpls_signaling": {
        "positive": [
            r"Operational",
            r"Up",
            r"Established",
            r"LDP.*operational",
            r"session.*established",
            r"label.*bound",
        ],
        "negative": [
            r"Down",
            r"Idle",
            r"Init",
            r"No LDP",
            r"session.*down",
            r"not established",
        ],
    },
    "lsp_transport": {
        "positive": [
            r"Up",
            r"Active",
            r"State:\s*Up",
            r"label.*switched",
            r"LSP.*up",
        ],
        "negative": [
            r"Down",
            r"Failed",
            r"No path",
            r"not active",
            r"State:\s*Down",
        ],
    },
    "bgp": {
        "positive": [
            r"Established",
            r"Up",
            r"Active",
            r"Neighbor.*up",
            r"BGP.*established",
        ],
        "negative": [
            r"Idle",
            r"Connect",
            r"Down",
            r"not established",
            r"peer.*down",
        ],
    },
    "mp_bgp_vpn": {
        "positive": [
            r"VPN.*Active",
            r"Established",
            r"Import.*OK",
            r"Route.*present",
            r"vpnv[46].*active",
        ],
        "negative": [
            r"No route",
            r"Import.*failed",
            r"Route.*missing",
            r"not established",
            r"VPN.*down",
        ],
    },
}


def parse_stage_output(stage: str, raw_output: str) -> dict[str, Any]:
    """Parse an output blob into normalized evidence for a validation stage."""
    stage_key = stage if stage in _STAGE_PATTERNS else "igp"
    patterns = _STAGE_PATTERNS[stage_key]

    positive_hits = []
    negative_hits = []

    for pattern in patterns["positive"]:
        if re.search(pattern, raw_output, flags=re.IGNORECASE | re.MULTILINE):
            positive_hits.append(pattern)

    for pattern in patterns["negative"]:
        if re.search(pattern, raw_output, flags=re.IGNORECASE | re.MULTILINE):
            negative_hits.append(pattern)

    status = "passed" if positive_hits and not negative_hits else "failed" if negative_hits else "unknown"

    evidence: list[str] = []
    if positive_hits:
        evidence.append(f"Positive indicators found: {', '.join(positive_hits[:3])}")
    if negative_hits:
        evidence.append(f"Failure indicators found: {', '.join(negative_hits[:3])}")
    if not evidence:
        evidence.append("No clear state indicators found in the command output.")

    return {
        "stage": stage_key,
        "status": status,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
        "evidence": evidence,
    }
