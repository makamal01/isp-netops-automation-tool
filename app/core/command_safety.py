"""Guard rail to keep this tool read-only for now: blocks anything that
looks like a configuration or disruptive command, regardless of vendor
syntax (IOS/IOS-XE/IOS-XR, VRP, SR OS). Engineers running show/display
commands are unaffected. Admins can disable this per-run via the GUI
"safe mode" checkbox once config support is intentionally added later.
"""
import re

_BLOCKED_PATTERNS = [
    r"^\s*conf(t|ig)?(\s|$)",     # configure / configure terminal / conf t
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

ALLOWED_PREFIXES = ("show", "display", "get", "ping", "traceroute", "info")


def is_command_safe(command: str) -> bool:
    cmd = command.strip()
    if not cmd:
        return False
    return _BLOCKED_RE.search(cmd) is None


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
