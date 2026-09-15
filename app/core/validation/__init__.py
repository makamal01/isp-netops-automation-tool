"""Layered MPLS/VPN path validation: runs each stage's command profile
against real devices over SSH and reports per-device pass/fail evidence.

This module lives alongside the bulk command runner and does not modify
its execution workflow, but reuses its device-connection primitives.
"""

from .engine import ValidationEngine
from .models import StageResult, ValidationRequest, ValidationResult

__all__ = ["ValidationEngine", "StageResult", "ValidationRequest", "ValidationResult"]
