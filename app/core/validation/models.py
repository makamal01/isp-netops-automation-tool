from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ValidationRequest:
    side_a: str
    side_b: str
    vendor: str
    platform: str
    service_type: str
    mode: str = "full_chain"
    protocol_focus: Optional[str] = None
    vrf: Optional[str] = None
    path_type: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None


@dataclass
class DeviceStageEvidence:
    """Per-device outcome for a single validation stage, so the operator can
    see which side of a path failed instead of only a merged stage verdict."""
    device_name: str
    host: str
    status: str  # passed, failed, unknown, connection_failed
    raw_output: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class StageResult:
    stage: str
    status: str
    vendor: str
    platform: str
    commands: list[str]
    raw_output: str
    parsed_summary: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    next_step: str = ""
    confidence: str = "medium"
    device_results: list[DeviceStageEvidence] = field(default_factory=list)


@dataclass
class ValidationResult:
    overall_status: str
    failed_stage: Optional[str]
    stage_results: list[StageResult]
    root_cause: str
    recommendation: str
    summary: str
