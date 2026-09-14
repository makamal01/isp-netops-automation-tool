from __future__ import annotations

from typing import List, Optional

from app.core.command_runner import open_jump_transport, run_commands_on_device
from app.core.jump_server import JumpServerConfig
from app.core.validation.command_profiles import get_profiles_for
from app.core.validation.models import StageResult, ValidationRequest, ValidationResult
from app.core.validation.parsers import parse_stage_output


class ValidationEngine:
    """Minimal validation engine scaffold for layered MPLS/VPN checks.

    This intentionally keeps the implementation conservative and isolated from the
    stable bulk command workflow already used by the GUI.
    """

    _stage_order = [
        "igp",
        "mpls_signaling",
        "lsp_transport",
        "bgp",
        "mp_bgp_vpn",
    ]

    def stage_order(self) -> List[str]:
        return list(self._stage_order)

    def validate(
        self,
        request: ValidationRequest,
        devices: Optional[list] = None,
        jump_config: Optional[JumpServerConfig] = None,
    ) -> ValidationResult:
        stage_results: list[StageResult] = []

        if devices:
            return self._validate_devices(request, devices, jump_config=jump_config)

        for stage_name in self._stage_order:
            profiles = get_profiles_for(request.vendor, request.platform, stage_name)
            if not profiles:
                stage_results.append(
                    StageResult(
                        stage=stage_name,
                        status="unknown",
                        vendor=request.vendor,
                        platform=request.platform,
                        commands=[],
                        raw_output="No command profile found for the selected vendor/platform/stage.",
                        parsed_summary={"status": "not_configured"},
                        evidence=["Command profile not available."],
                        next_step="Add a vendor command profile for this validation stage.",
                        confidence="low",
                    )
                )
                continue

            profile = profiles[0]
            stage_result = StageResult(
                stage=stage_name,
                status="passed",
                vendor=request.vendor,
                platform=request.platform,
                commands=profile.command_list,
                raw_output="Profile selected successfully; command execution not yet wired to a live device.",
                parsed_summary={
                    "protocol": profile.protocol,
                    "status": "passed",
                    "success_indicators": profile.success_indicators,
                },
                evidence=["Validation scaffold is active for this stage."],
                next_step="Proceed with the next validation stage.",
                confidence="medium",
            )
            stage_results.append(stage_result)

        return ValidationResult(
            overall_status="passed",
            failed_stage=None,
            stage_results=stage_results,
            root_cause="None detected in scaffold mode.",
            recommendation="Connect this validation engine to real device command execution in a later implementation phase.",
            summary="Validation stages were initialized successfully in the proof-of-concept scaffold.",
        )

    def _validate_devices(
        self,
        request: ValidationRequest,
        devices: list,
        jump_config: Optional[JumpServerConfig] = None,
    ) -> ValidationResult:
        stage_results: list[StageResult] = []
        stage_name = request.protocol_focus.lower().replace("/", "_").replace(" ", "_") if request.protocol_focus else "igp"

        # Mirror run_bulk(): log into the jump host once (if configured) and
        # reuse that transport for every device/stage in this validation run,
        # instead of trying to reach devices directly from this machine.
        jump_client = None
        jump_transport = None
        if jump_config and jump_config.enabled:
            jump_client = open_jump_transport(jump_config)
            jump_transport = jump_client.get_transport()

        if request.protocol_focus:
            requested_stage = {
                "IGP": "igp",
                "MPLS": "mpls_signaling",
                "LSP": "lsp_transport",
                "BGP": "bgp",
                "MP-BGP/VPN": "mp_bgp_vpn",
            }.get(request.protocol_focus)
            if requested_stage:
                stage_name = requested_stage

        relevant_stages = [stage_name] if stage_name in self._stage_order else self._stage_order
        if request.mode == "single_stage":
            relevant_stages = [stage_name] if stage_name in self._stage_order else self._stage_order
        else:
            relevant_stages = list(self._stage_order)

        try:
            for stage in relevant_stages:
                profiles = get_profiles_for(request.vendor, request.platform, stage)
                if not profiles:
                    stage_results.append(
                        StageResult(
                            stage=stage,
                            status="unknown",
                            vendor=request.vendor,
                            platform=request.platform,
                            commands=[],
                            raw_output="No command profile found.",
                            parsed_summary={"status": "not_configured"},
                            evidence=["No command profile for this vendor/platform/stage."],
                            next_step="Add a command profile for this stage.",
                            confidence="low",
                        )
                    )
                    continue

                profile = profiles[0]
                collected_outputs = []
                success_for_all = True
                failure_messages = []
                for device in devices:
                    try:
                        result = run_commands_on_device(device, profile.command_list, jump_transport=jump_transport)
                    except Exception as exc:  # pragma: no cover - surfaced to the validation UI
                        result = None
                        failure_messages.append(f"{device.name}@{device.host}: SSH connection failed: {exc}")
                        success_for_all = False
                        continue

                    if result is not None:
                        collected_outputs.append(f"{device.name}: {result.output}")
                        if not result.success:
                            success_for_all = False
                            failure_messages.append(f"{device.name}@{device.host}: {result.error or 'device command execution failed'}")

                raw_output = "\n".join(collected_outputs)
                if not success_for_all:
                    evidence = []
                    if failure_messages:
                        evidence.extend(failure_messages)
                    evidence.append("Device execution failed or returned an unsuccessful result.")
                    parsed = {"status": "failed", "evidence": evidence}
                    stage_status = "failed"
                else:
                    parsed = parse_stage_output(stage, raw_output)
                    stage_status = parsed["status"]
                    if stage_status == "unknown":
                        parsed = {
                            "status": "failed",
                            "evidence": [
                                f"No valid {stage} state was detected from the configured devices. "
                                "The network may be incomplete or the relevant protocol is not present."
                            ],
                        }
                        stage_status = "failed"

                stage_result = StageResult(
                    stage=stage,
                    status=stage_status,
                    vendor=request.vendor,
                    platform=request.platform,
                    commands=profile.command_list,
                    raw_output=raw_output,
                    parsed_summary={
                        "protocol": profile.protocol,
                        "status": stage_status,
                        "devices_checked": len(devices),
                        **parsed,
                    },
                    evidence=parsed["evidence"],
                    next_step="Proceed to the next validation stage." if stage_status == "passed" else "Fix the failing lower-layer prerequisite before proceeding.",
                    confidence="high" if stage_status == "passed" else "medium",
                )
                stage_results.append(stage_result)
        finally:
            if jump_client:
                jump_client.close()

        overall_status = "passed"
        failed_stage = None
        for stage_result in stage_results:
            if stage_result.status == "failed":
                overall_status = "failed"
                failed_stage = stage_result.stage
                break

        return ValidationResult(
            overall_status=overall_status,
            failed_stage=failed_stage,
            stage_results=stage_results,
            root_cause="No lower-layer issue detected." if failed_stage is None else f"Stage '{failed_stage}' failed during validation.",
            recommendation="Continue validation after fixing the failed stage." if failed_stage is None else "Resolve the failed layer before continuing to higher-layer checks.",
            summary=f"Validation completed with status {overall_status}.",
        )
