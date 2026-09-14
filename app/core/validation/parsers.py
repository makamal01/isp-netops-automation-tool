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
            r"\bDOWN\b",
            r"\bINIT\b",
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
            r"\bOper\b",  # Cisco IOS-XE abbreviates "State: Operational" to "State: Oper"
            r"Up",
            r"Established",
            r"LDP.*operational",
            r"session.*established",
            r"label.*bound",
        ],
        "negative": [
            r"\bDown\b",  # word-bounded: LDP's "Downstream" label mode is healthy, not a failure
            r"Idle",
            r"Init",
            r"No LDP",
            r"session.*down",
            r"not established",
        ],
        # RSVP-TE/tunnel process being off is a normal LDP-only deployment
        # choice, not a signaling failure. These phrases are stripped before
        # negative-keyword matching so LDP-only labs (e.g. "RSVP Process:
        # not running") can't be mistaken for a down/broken session.
        "neutral": [
            r"RSVP Process:\s*not running",
            r"LSP Tunnels Process:\s*not running[^\n]*",
            r"not registered with RSVP",
            r"Forwarding:\s*disabled",
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
            r"\bDown\b",
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
            r"\bDown\b",
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

    # Phrases that describe an optional sub-protocol being intentionally
    # unused (e.g. RSVP-TE in an LDP-only deployment) are informational, not
    # failures. Record them, then remove them from the text negative-keyword
    # matching runs against, so their wording can never flip the stage to
    # "failed" for a condition that isn't actually a problem.
    neutral_hits = []
    negative_scan_text = raw_output
    for pattern in patterns.get("neutral", []):
        if re.search(pattern, raw_output, flags=re.IGNORECASE | re.MULTILINE):
            neutral_hits.append(pattern)
        negative_scan_text = re.sub(pattern, "", negative_scan_text, flags=re.IGNORECASE | re.MULTILINE)

    # positive_hits/negative_hits track which *patterns* fired (used for the
    # pass/fail decision below); the human-facing evidence text is built from
    # the actual matched substrings instead, so an operator sees real device
    # output (e.g. "State: Oper") rather than a raw regex like "\bOper\b".
    positive_hits = []
    positive_matches = []
    negative_hits = []
    negative_matches = []

    for pattern in patterns["positive"]:
        match = re.search(pattern, raw_output, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            positive_hits.append(pattern)
            positive_matches.append(match.group(0).strip())

    for pattern in patterns["negative"]:
        match = re.search(pattern, negative_scan_text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            negative_hits.append(pattern)
            negative_matches.append(match.group(0).strip())

    status = "passed" if positive_hits and not negative_hits else "failed" if negative_hits else "unknown"

    evidence: list[str] = []
    if positive_matches:
        shown = list(dict.fromkeys(positive_matches))[:3]
        evidence.append(f"Positive indicators found: {', '.join(shown)}")
    if neutral_hits:
        evidence.append(
            "Optional sub-protocol not in use on this path (e.g. RSVP-TE in an "
            "LDP-only deployment) - not treated as a failure."
        )
    if negative_matches:
        shown = list(dict.fromkeys(negative_matches))[:3]
        evidence.append(f"Failure indicators found: {', '.join(shown)}")
    if not evidence:
        evidence.append("No clear state indicators found in the command output.")

    return {
        "stage": stage_key,
        "status": status,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
        "neutral_hits": neutral_hits,
        "evidence": evidence,
    }
