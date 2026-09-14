from app.core.device_manager import Device
from app.core.validation.engine import ValidationEngine
from app.core.validation.models import StageResult, ValidationRequest, ValidationResult
from app.utils import crypto


def test_validation_request_defaults():
    req = ValidationRequest(
        side_a="10.0.0.1",
        side_b="10.0.0.2",
        vendor="Cisco",
        platform="IOS-XR",
        service_type="L3VPN",
    )

    assert req.mode == "full_chain"
    assert req.protocol_focus is None
    assert req.vrf is None


def test_validation_engine_builds_stage_order():
    engine = ValidationEngine()
    stages = engine.stage_order()

    assert stages[0] == "igp"
    assert stages[-1] == "mp_bgp_vpn"


def test_stage_result_and_validation_result_models():
    stage = StageResult(
        stage="igp",
        status="passed",
        vendor="Cisco",
        platform="IOS-XR",
        commands=["show ospf neighbor"],
        raw_output="Neighbor is up",
        parsed_summary={"neighbor_state": "full"},
        evidence=["neighbor is full"],
        next_step="Proceed to MPLS signaling validation",
        confidence="high",
    )

    result = ValidationResult(
        overall_status="passed",
        failed_stage=None,
        stage_results=[stage],
        root_cause="None detected",
        recommendation="continue",
        summary="Path healthy",
    )

    assert stage.status == "passed"
    assert result.overall_status == "passed"


def test_validation_engine_runs_stage_profiles_for_devices(monkeypatch):
    device = Device(
        name="core-rtr-01",
        host="10.0.0.1",
        vendor="Cisco IOS",
        username="admin",
        password_encrypted=crypto.encrypt("secret"),
    )

    captured = []

    def fake_run_commands_on_device(dev, commands, **kwargs):
        captured.append((dev.name, commands))
        output = "Neighbor is up\nAdjacency is full"
        raw = "show ospf neighbor\nNeighbor is up\nAdjacency is full"

        if any("mpls" in cmd.lower() for cmd in commands):
            output = "LDP session is established\nLSP is up\nOperational"
            raw = "show mpls ldp neighbor\nLDP session is established\nLSP is up"
        elif any("bgp" in cmd.lower() for cmd in commands):
            output = "BGP neighbor is established\nState: Up\nPeer is ready"
            raw = "show bgp summary\nBGP neighbor is established\nState: Up"
        elif any("vpn" in cmd.lower() for cmd in commands):
            output = "VPN route is present\nMP-BGP is established\nImport OK"
            raw = "show bgp vpnv4 unicast summary\nVPN route is present\nMP-BGP is established"
        elif any("route" in cmd.lower() for cmd in commands):
            output = "Route is present\nNext hop reachable"
            raw = "show ip route 10.0.0.2\nRoute is present"

        return type(
            "Result",
            (),
            {
                "device_name": dev.name,
                "host": dev.host,
                "success": True,
                "output": output,
                "duration_seconds": 1.0,
                "error": "",
                "raw_output": raw,
            },
        )()

    monkeypatch.setattr("app.core.validation.engine.run_commands_on_device", fake_run_commands_on_device)

    engine = ValidationEngine()
    request = ValidationRequest(
        side_a="10.0.0.1",
        side_b="10.0.0.2",
        vendor="Cisco",
        platform="IOS-XR",
        service_type="L3VPN",
        mode="full_chain",
        protocol_focus="IGP",
    )

    result = engine.validate(request, devices=[device])

    assert result.overall_status == "passed"
    assert len(result.stage_results) == 5
    assert result.stage_results[0].stage == "igp"
    assert result.stage_results[0].status == "passed"
    assert captured[0][0] == "core-rtr-01"
    assert captured[0][1] == ["show ospf neighbor", "show isis neighbors", "show ip route 10.0.0.2"]
    assert captured[-1][1] == ["show bgp vpnv4 unicast summary", "show route table vpnv4", "show vrf"]


def test_stage_parser_detects_positive_and_negative_signals():
    from app.core.validation.parsers import parse_stage_output

    good = parse_stage_output("igp", "Neighbor is up\nAdjacency is full\nRoute is present")
    bad = parse_stage_output("bgp", "Idle\nNeighbor is down")

    assert good["status"] == "passed"
    assert bad["status"] == "failed"


def test_single_stage_mode_only_runs_selected_stage(monkeypatch):
    device = Device(
        name="core-rtr-01",
        host="10.0.0.1",
        vendor="Cisco IOS",
        username="admin",
        password_encrypted=crypto.encrypt("secret"),
    )

    called = []

    def fake_run_commands_on_device(dev, commands, **kwargs):
        called.append(commands)
        return type(
            "Result",
            (),
            {
                "device_name": dev.name,
                "host": dev.host,
                "success": True,
                "output": "Neighbor is up",
                "duration_seconds": 1.0,
                "error": "",
                "raw_output": "Neighbor is up",
            },
        )()

    monkeypatch.setattr("app.core.validation.engine.run_commands_on_device", fake_run_commands_on_device)

    engine = ValidationEngine()
    request = ValidationRequest(
        side_a="10.0.0.1",
        side_b="10.0.0.2",
        vendor="Cisco",
        platform="IOS-XR",
        service_type="L3VPN",
        mode="single_stage",
        protocol_focus="IGP",
    )

    result = engine.validate(request, devices=[device])

    assert result.overall_status == "passed"
    assert len(result.stage_results) == 1
    assert result.stage_results[0].stage == "igp"
    assert called


def test_failed_device_execution_preserves_failure_status(monkeypatch):
    device = Device(
        name="core-rtr-01",
        host="10.0.0.1",
        vendor="Cisco IOS",
        username="admin",
        password_encrypted=crypto.encrypt("secret"),
    )

    def fake_run_commands_on_device(dev, commands, **kwargs):
        return type(
            "Result",
            (),
            {
                "device_name": dev.name,
                "host": dev.host,
                "success": False,
                "output": "",
                "duration_seconds": 1.0,
                "error": "Authentication failed",
                "raw_output": "",
            },
        )()

    monkeypatch.setattr("app.core.validation.engine.run_commands_on_device", fake_run_commands_on_device)

    engine = ValidationEngine()
    request = ValidationRequest(
        side_a="10.0.0.1",
        side_b="10.0.0.2",
        vendor="Cisco",
        platform="IOS-XR",
        service_type="L3VPN",
        mode="full_chain",
        protocol_focus="IGP",
    )

    result = engine.validate(request, devices=[device])

    assert result.overall_status == "failed"
    assert result.failed_stage == "igp"
    assert "Authentication failed" in result.stage_results[0].evidence[0]


def test_per_device_breakdown_identifies_which_side_failed(monkeypatch):
    """One device up, one device down: the stage must fail overall, but the
    per-device breakdown must show exactly which side is the problem -
    not just a merged pass/fail for the whole stage."""
    device_a = Device(
        name="side-a",
        host="10.0.0.1",
        vendor="Cisco IOS",
        username="admin",
        password_encrypted=crypto.encrypt("secret"),
    )
    device_b = Device(
        name="side-b",
        host="10.0.0.2",
        vendor="Cisco IOS",
        username="admin",
        password_encrypted=crypto.encrypt("secret"),
    )

    def fake_run_commands_on_device(dev, commands, **kwargs):
        if dev.name == "side-a":
            output = "Neighbor is up\nAdjacency is full"
        else:
            output = "Neighbor is down\nAdjacency Idle"
        return type(
            "Result",
            (),
            {
                "device_name": dev.name,
                "host": dev.host,
                "success": True,
                "output": output,
                "duration_seconds": 1.0,
                "error": "",
                "raw_output": output,
            },
        )()

    monkeypatch.setattr("app.core.validation.engine.run_commands_on_device", fake_run_commands_on_device)

    engine = ValidationEngine()
    request = ValidationRequest(
        side_a="10.0.0.1",
        side_b="10.0.0.2",
        vendor="Cisco",
        platform="IOS-XR",
        service_type="L3VPN",
        mode="single_stage",
        protocol_focus="IGP",
    )

    result = engine.validate(request, devices=[device_a, device_b])

    igp_stage = result.stage_results[0]
    assert igp_stage.status == "failed"
    assert len(igp_stage.device_results) == 2

    by_name = {dr.device_name: dr for dr in igp_stage.device_results}
    assert by_name["side-a"].status == "passed"
    assert by_name["side-b"].status == "failed"
    assert any("[side-b]" in item for item in igp_stage.evidence)


def test_cisco_iosxe_alias_uses_cisco_profiles():
    from app.core.validation.command_profiles import get_profiles_for

    profiles = get_profiles_for("Cisco IOS-XE", "IOS-XE", "igp")

    assert profiles
    assert profiles[0].vendor == "Cisco"
    assert profiles[0].stage == "igp"


def test_validation_engine_handles_connection_errors_without_crashing(monkeypatch):
    device = Device(
        name="core-rtr-01",
        host="10.0.0.1",
        vendor="Cisco IOS",
        username="admin",
        password_encrypted=crypto.encrypt("secret"),
    )

    def fake_run_commands_on_device(dev, commands, **kwargs):
        raise RuntimeError("SSH connection failed: network unreachable")

    monkeypatch.setattr("app.core.validation.engine.run_commands_on_device", fake_run_commands_on_device)

    engine = ValidationEngine()
    request = ValidationRequest(
        side_a="10.0.0.1",
        side_b="10.0.0.2",
        vendor="Cisco IOS-XE",
        platform="IOS-XE",
        service_type="L3VPN",
        mode="full_chain",
        protocol_focus="IGP",
    )

    result = engine.validate(request, devices=[device])

    assert result.overall_status == "failed"
    assert result.failed_stage == "igp"
    assert "SSH connection failed" in result.stage_results[0].evidence[0]


def test_command_profiles_cover_multi_vendor_stage_library():
    from app.core.validation.command_profiles import get_profiles_for

    cisco_profiles = get_profiles_for("Cisco", "IOS-XR")
    huawei_profiles = get_profiles_for("Huawei", "VRP")

    stage_names = {profile.stage for profile in cisco_profiles}
    assert {"igp", "mpls_signaling", "lsp_transport", "bgp", "mp_bgp_vpn"}.issubset(stage_names)
    assert any(profile.stage == "bgp" for profile in huawei_profiles)
    assert any("display bgp vpnv4 all routing-table" in profile.command_list for profile in huawei_profiles)
