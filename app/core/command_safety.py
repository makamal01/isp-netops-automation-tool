"""Guard rail for read-only operations: reject obvious disruptive commands.

Safe mode is a per-run option in the GUI. This is a pattern filter, not a
complete vendor-aware allowlist, so write-enabled workflows need a separate
authorization design before they are introduced.
"""
import re

from app.core.deployment_policy import get_deployment_policy

_BLOCKED_PATTERNS = [
    r"^\s*conf(ig(ure)?)?\b",     # conf / conf t / config t / configure terminal
    r"\bwrite\s+erase\b",
    r"\breload\b",
    r"\breboot\b",
    r"\bdelete\b",
    r"\bformat\b",
    r"^\s*clear\b",
    r"\bno\s+shutdown\b",
    r"\bshutdown\b",
    r"\berase\b",
    r"\bcopy\b.*\brunning\b",
    r"\badmin\b.*\b(reboot|reset)\b",
]

_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)


def is_command_safe(command: str) -> bool:
    """Reject disruptive commands unless an explicit enterprise exception is enabled.

    Only the command itself is checked against the blocked patterns, not any
    display filter after a pipe (e.g. 'show interfaces | include shutdown').
    A pipe filter narrows the output of a read-only show/display command; it
    can't turn it into a disruptive operation, so matching against the whole
    string would reject ordinary NOC commands for mentioning a blocked word
    as a search term.
    """
    cmd = command.strip()
    if not cmd:
        return False
    policy = get_deployment_policy()
    if policy.allow_unsafe_commands:
        return True
    command_part = cmd.split("|", 1)[0]
    return _BLOCKED_RE.search(command_part) is None


def filter_safe_commands(commands):
    """Return (safe, rejected) command lists."""
    safe, rejected = [], []
    for c in commands:
        c = c.strip()
        if not c:
            continue
        if is_command_safe(c):
            safe.append(c)
        else:
            rejected.append(c)
    return safe, rejected
