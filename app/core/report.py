"""Builds a single, human-readable text report for a bulk command run —
suitable for attaching to a ticket or archiving for audit purposes."""
from datetime import datetime, timezone
from typing import List, Dict

from app.core.command_runner import DeviceResult

SECTION_LINE = "=" * 36


def _command_heading(command: str) -> str:
    return f"{SECTION_LINE}\nCOMMAND: {command}\n{SECTION_LINE}"


def _command_output(output: str, command: str, commands: List[str]) -> str:
    """Extract one command block from either current raw or legacy output."""
    marker = f"--- {command} ---"
    heading = _command_heading(command)
    marker_start = output.find(marker)
    heading_start = output.find(heading)
    if heading_start >= 0 and (marker_start < 0 or heading_start < marker_start):
        start = heading_start + len(heading)
        end = len(output)
        for next_command in commands:
            if next_command == command:
                continue
            next_heading = output.find(
                _command_heading(next_command),
                start,
            )
            if next_heading >= 0:
                end = min(end, next_heading)
        return output[start:end].strip()

    start = output.find(marker)
    if start < 0:
        return output.strip()

    start += len(marker)
    end = len(output)
    for next_command in commands:
        if next_command == command:
            continue
        next_marker = output.find(f"--- {next_command} ---", start)
        if next_marker >= 0:
            end = min(end, next_marker)
    return output[start:end].strip()


def format_device_output(result: DeviceResult, commands: List[str], raw: bool = False) -> str:
    """Format one device's output as parsed or raw operational evidence."""
    if not result.success:
        return f"ERROR: {result.error}"

    source_output = result.raw_output if raw and result.raw_output else result.output
    if not raw:
        sections = []
        for command in commands:
            sections.append(f"--- {command} ---\n{_command_output(source_output, command, commands)}")
        return "\n\n".join(sections) + "\n"

    lines = []
    for command in commands:
        lines.extend(("", _command_heading(command), _command_output(source_output, command, commands)))
    return "\n".join(lines).lstrip() + "\n"


def build_text_report(
    username: str,
    commands: List[str],
    results_by_device: Dict[str, DeviceResult],
    safe_mode: bool,
    include_output: bool = True,
) -> str:
    """Build a report while optionally omitting output duplicated in export files."""
    lines = []
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    success_count = sum(1 for r in results_by_device.values() if r.success)
    lines.append("=" * 70)
    lines.append("ISP NETOPS TOOL | COMMAND EXECUTION REPORT")
    lines.append("=" * 70)
    lines.append(f"Report generated (UTC): {run_at}")
    lines.append(f"Operator:               {username}")
    lines.append(f"Safe mode:              {'ENABLED' if safe_mode else 'DISABLED'}")
    lines.append(f"Devices requested:      {len(results_by_device)}")
    lines.append(f"Devices successful:     {success_count}")
    lines.append(f"Devices failed:         {len(results_by_device) - success_count}")
    lines.append("")
    lines.append("COMMANDS EXECUTED")
    lines.append("-" * 70)
    for cmd in commands:
        lines.append(f"{cmd}")
    lines.append("")

    lines.append("DEVICE RESULTS")
    lines.append("-" * 70)
    for name, result in results_by_device.items():
        lines.append("")
        lines.append(f"DEVICE: {name}")
        lines.append(f"HOST:   {result.host}")
        lines.append(f"STATUS: {'SUCCESS' if result.success else 'FAILED'}")
        lines.append(f"DURATION: {result.duration_seconds:.2f}s")
        if result.success:
            lines.append("OUTPUT FILES: parsed and raw device files")
            if include_output:
                lines.append("OUTPUT: RAW ROUTER RESPONSE")
                lines.append(format_device_output(result, commands, raw=True).rstrip())
        else:
            lines.append(f"ERROR: {result.error}")
    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)
