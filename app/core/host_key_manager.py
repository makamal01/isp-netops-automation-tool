"""Manual SSH host-key enrollment.

Fetches the key a host presents during the SSH transport handshake -
without authenticating or running any command - so an operator can see its
fingerprint and explicitly confirm trust before the app will use it. This
automates the "obtain and verify the key through an approved channel" step
DEVELOPER_TECHNICAL_GUIDE.md already requires; it replaces manually running
ssh-keyscan and hand-editing the known_hosts file, not the verification
judgment call itself.
"""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Optional

from paramiko import Transport

from app.config import KNOWN_HOSTS_FILE, DEFAULT_SSH_TIMEOUT, atomic_write_text


@dataclass
class HostKeyInfo:
    host: str
    key_type: str
    key_base64: str
    fingerprint: str


def fetch_host_key(
    host: str,
    port: int = 22,
    timeout: int = DEFAULT_SSH_TIMEOUT,
    jump_transport: Optional[object] = None,
) -> HostKeyInfo:
    """Negotiate just the SSH transport handshake to see `host`'s presented
    key. If `jump_transport` is given, reach the host through a proxied
    channel (matching how device/validation runs reach it) instead of
    connecting directly from this machine.
    """
    if jump_transport is not None:
        sock = jump_transport.open_channel(
            "direct-tcpip", (host, port), ("127.0.0.1", 0), timeout=timeout,
        )
    else:
        sock = (host, port)

    transport = Transport(sock)
    try:
        transport.start_client(timeout=timeout)
        key = transport.get_remote_server_key()
    finally:
        transport.close()

    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
    return HostKeyInfo(host=host, key_type=key.get_name(), key_base64=key.get_base64(), fingerprint=fingerprint)


def trust_host_key(info: HostKeyInfo) -> None:
    """Record `info` as the trusted key for its host: replaces any existing
    entry for that host (a stale/changed key) or adds a new one."""
    existing_lines = []
    if KNOWN_HOSTS_FILE.exists():
        existing_lines = KNOWN_HOSTS_FILE.read_text(encoding="utf-8").splitlines()
    kept = [line for line in existing_lines if line.strip() and line.split()[0] != info.host]
    kept.append(f"{info.host} {info.key_type} {info.key_base64}")
    atomic_write_text(KNOWN_HOSTS_FILE, "\n".join(kept) + "\n")
