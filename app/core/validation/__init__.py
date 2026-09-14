"""Layered MPLS/VRF validation feature scaffolding.

This module intentionally lives alongside the current command runner and does not
modify the stable existing bulk command execution workflow.
"""

from .engine import ValidationEngine
from .models import StageResult, ValidationRequest, ValidationResult

__all__ = ["ValidationEngine", "StageResult", "ValidationRequest", "ValidationResult"]
