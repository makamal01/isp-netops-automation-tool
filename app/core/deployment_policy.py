"""Enterprise deployment policy for managed-laptop installation.

The app is designed to run on approved managed Windows laptops and to reach
routers through a bastion/jumpserver path. This module codifies the default
safety posture expected by enterprise IT and security reviewers.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeploymentPolicy:
    """Default policy for an org-approved deployment."""

    install_target: str = "managed_laptop"
    require_signed_installer: bool = True
    require_admin_rights: bool = False
    safe_mode_default: bool = True
    jumpserver_required: bool = True
    allow_unsafe_commands: bool = False

    def requires_approval_for(self, command: str) -> bool:
        """Return whether a command should be treated as admin-approved-only."""
        cmd = (command or "").strip().lower()
        if not cmd:
            return False

        high_risk_tokens = (
            "configure",
            "configure terminal",
            "reload",
            "reboot",
            "write erase",
            "erase",
            "delete",
            "shutdown",
            "clear",
            "copy running",
            "no shutdown",
        )
        return any(token in cmd for token in high_risk_tokens)


def get_deployment_policy() -> DeploymentPolicy:
    """Singleton-like accessor used by the app runtime."""
    return DeploymentPolicy()
