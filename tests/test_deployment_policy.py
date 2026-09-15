from app.core.deployment_policy import DeploymentPolicy


def test_deployment_policy_defaults_are_safe_and_org_approved():
    policy = DeploymentPolicy()

    assert policy.install_target == "managed_laptop"
    assert policy.require_signed_installer is True
    assert policy.require_admin_rights is False
    assert policy.safe_mode_default is True
    assert policy.jumpserver_required is True
    assert policy.allow_unsafe_commands is False


def test_deployment_policy_flags_unsafe_actions_for_review():
    policy = DeploymentPolicy()

    assert policy.requires_approval_for("configure terminal") is True
    assert policy.requires_approval_for("reload") is True
    assert policy.requires_approval_for("show version") is False
