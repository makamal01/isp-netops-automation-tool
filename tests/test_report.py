"""Compatibility tests for parsed, raw, and summary report formats."""

from app.core.command_runner import DeviceResult
from app.core.report import build_text_report, format_device_output


def test_report_uses_each_command_as_an_output_section_heading():
    result = DeviceResult(
        device_name="lab-router",
        host="192.0.2.1",
        success=True,
        output=(
            "--- show version ---\nIOS-XE raw version output\n"
            "\n--- show ip interface brief ---\nGigabitEthernet1 up up\n"
        ),
        duration_seconds=0.1,
        raw_output=(
            "====================================\nCOMMAND: show version\n====================================\n"
            "RAW show version\n"
            "\n====================================\nCOMMAND: show ip interface brief\n====================================\n"
            "RAW interface output\n"
        ),
    )

    report = build_text_report(
        username="admin",
        commands=["show version", "show ip interface brief"],
        results_by_device={"lab-router": result},
        safe_mode=True,
    )

    assert "====================================\nCOMMAND: show version\n====================================" in report
    assert "RAW show version" in report
    assert "====================================\nCOMMAND: show ip interface brief\n====================================" in report
    assert "RAW interface output" in report


def test_parsed_device_file_uses_legacy_command_sections():
    result = DeviceResult(
        device_name="lab-router",
        host="192.0.2.1",
        success=True,
        output="--- show ip int brief ---\n[\n  {\"interface\": \"GigabitEthernet1\"}\n]\n",
        duration_seconds=0.1,
    )

    output = format_device_output(result, ["show ip int brief"])

    assert output == (
        "--- show ip int brief ---\n"
        "[\n  {\"interface\": \"GigabitEthernet1\"}\n]\n"
    )


def test_raw_and_parsed_outputs_remain_distinct():
    result = DeviceResult(
        device_name="lab-router",
        host="192.0.2.1",
        success=True,
        output="--- show version ---\n[{\"version\": \"16.12.3\"}]\n",
        duration_seconds=0.1,
        raw_output="====================================\nCOMMAND: show version\n====================================\nVersion 16.12.3\n",
    )

    parsed = format_device_output(result, ["show version"])
    raw = format_device_output(result, ["show version"], raw=True)

    assert parsed.startswith("--- show version ---")
    assert "[{'version'" not in raw
    assert raw.startswith("====================================\nCOMMAND: show version")


def test_export_report_can_be_summary_only():
    result = DeviceResult(
        device_name="lab-router",
        host="192.0.2.1",
        success=True,
        output="--- show version ---\n[{\"version\": \"16.12.3\"}]\n",
        duration_seconds=0.1,
        raw_output="====================================\nCOMMAND: show version\n====================================\nVersion 16.12.3\n",
    )

    report = build_text_report(
        "admin", ["show version"], {"lab-router": result}, True, include_output=False,
    )

    assert "OUTPUT FILES: parsed and raw device files" in report
    assert "OUTPUT: RAW ROUTER RESPONSE" not in report
    assert "Version 16.12.3" not in report