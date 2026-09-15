"""Safe-mode filtering: block real disruptive commands without rejecting
read-only show/display commands that merely mention a blocked word inside
a display filter (e.g. '| include shutdown')."""

from app.core.command_safety import filter_safe_commands, is_command_safe


def test_show_command_with_pipe_filter_mentioning_blocked_word_is_safe():
    """'show interfaces | include shutdown' is a standard read-only NOC
    command to find admin-down ports - it must not be treated as disruptive
    just because the filter argument contains the word "shutdown"."""
    assert is_command_safe("show interfaces | include shutdown") is True
    assert is_command_safe("show running-config | include delete") is True
    assert is_command_safe("display current-configuration | include clear") is True
    assert is_command_safe("show log | include reload") is True


def test_actual_disruptive_commands_are_still_blocked():
    for cmd in [
        "shutdown",
        "no shutdown",
        "configure terminal",
        "conf t",
        "reload",
        "reboot",
        "write erase",
        "erase startup-config",
        "delete flash:old.bin",
        "clear counters",
        "format flash:",
    ]:
        assert is_command_safe(cmd) is False, f"expected {cmd!r} to be blocked"


def test_ordinary_show_commands_are_safe():
    for cmd in ["show version", "show ip interface brief", "display version"]:
        assert is_command_safe(cmd) is True


def test_filter_safe_commands_partitions_mixed_input():
    safe, rejected = filter_safe_commands([
        "show interfaces | include shutdown",
        "reload",
        "show version",
    ])
    assert safe == ["show interfaces | include shutdown", "show version"]
    assert rejected == ["reload"]
