"""Manual SSH host-key enrollment: fetch a presented key without
authenticating, and record an operator-confirmed key as trusted."""

import base64
import hashlib

import paramiko

from app.core import host_key_manager
from app.core.host_key_manager import HostKeyInfo, fetch_host_key, is_host_key_failure, trust_host_key


class FakeKey:
    def __init__(self, name="ssh-ed25519", b64="AAAAC3NzaC1lZDI1NTE5AAAAIQfakekeybytes==", raw=b"fake-key-bytes"):
        self._name = name
        self._b64 = b64
        self._raw = raw

    def get_name(self):
        return self._name

    def get_base64(self):
        return self._b64

    def asbytes(self):
        return self._raw


class FakeTransport:
    instances = []

    def __init__(self, sock):
        self.sock = sock
        self.started = False
        self.closed = False
        self.key = FakeKey()
        FakeTransport.instances.append(self)

    def start_client(self, timeout=None):
        self.started = True
        self.timeout = timeout

    def get_remote_server_key(self):
        return self.key

    def close(self):
        self.closed = True


def test_fetch_host_key_negotiates_without_authenticating(monkeypatch):
    FakeTransport.instances.clear()
    monkeypatch.setattr(host_key_manager, "Transport", FakeTransport)

    info = fetch_host_key("10.0.0.1", port=22, timeout=5)

    transport = FakeTransport.instances[0]
    assert transport.sock == ("10.0.0.1", 22)
    assert transport.started is True
    assert transport.closed is True
    assert not hasattr(transport, "auth_password")  # never authenticates

    assert info.host == "10.0.0.1"
    assert info.key_type == "ssh-ed25519"
    expected_fp = "SHA256:" + base64.b64encode(hashlib.sha256(b"fake-key-bytes").digest()).decode().rstrip("=")
    assert info.fingerprint == expected_fp


def test_fetch_host_key_via_jump_transport_opens_proxied_channel(monkeypatch):
    FakeTransport.instances.clear()
    monkeypatch.setattr(host_key_manager, "Transport", FakeTransport)

    opened = {}

    class FakeJumpTransport:
        def open_channel(self, kind, dest, origin, timeout=None):
            opened["kind"] = kind
            opened["dest"] = dest
            opened["timeout"] = timeout
            return "fake-channel"

    fetch_host_key("10.246.111.1", port=22, timeout=8, jump_transport=FakeJumpTransport())

    assert opened == {"kind": "direct-tcpip", "dest": ("10.246.111.1", 22), "timeout": 8}
    assert FakeTransport.instances[0].sock == "fake-channel"


def test_trust_host_key_adds_new_entry(tmp_path, monkeypatch):
    known_hosts = tmp_path / "known_hosts"
    monkeypatch.setattr(host_key_manager, "KNOWN_HOSTS_FILE", known_hosts)

    trust_host_key(HostKeyInfo(host="10.0.0.1", key_type="ssh-rsa", key_base64="AAAA1", fingerprint="SHA256:x"))

    assert known_hosts.read_text(encoding="utf-8").strip() == "10.0.0.1 ssh-rsa AAAA1"


def test_trust_host_key_replaces_stale_entry_for_same_host_only(tmp_path, monkeypatch):
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text(
        "10.0.0.1 ssh-rsa OLDKEY\n10.0.0.2 ssh-rsa OTHERKEY\n", encoding="utf-8",
    )
    monkeypatch.setattr(host_key_manager, "KNOWN_HOSTS_FILE", known_hosts)

    trust_host_key(HostKeyInfo(host="10.0.0.1", key_type="ssh-ed25519", key_base64="NEWKEY", fingerprint="SHA256:y"))

    lines = known_hosts.read_text(encoding="utf-8").splitlines()
    assert "10.0.0.1 ssh-ed25519 NEWKEY" in lines
    assert "10.0.0.2 ssh-rsa OTHERKEY" in lines
    assert not any(line.startswith("10.0.0.1 ssh-rsa OLDKEY") for line in lines)
    assert len(lines) == 2


def test_is_host_key_failure_recognizes_device_result_error_prefixes():
    """Matches the exact prefixes command_runner.py's error taxonomy uses
    for host-key problems, so a device Test Connection can tell a host-key
    failure apart from auth/timeout/unexpected failures."""
    assert is_host_key_failure("SSH host-key error: Server '10.0.0.1' not found in known_hosts.") is True
    assert is_host_key_failure("SSH host-key or protocol error: some detail") is True
    assert is_host_key_failure("Authentication failed: bad password") is False
    assert is_host_key_failure("Connection timed out: no route to host") is False
    assert is_host_key_failure("Unexpected error: boom") is False


def test_is_host_key_failure_recognizes_reject_policy_exception():
    """Matches paramiko.RejectPolicy's own wording for an unrecognized
    host, used by the JumpServer connection path."""
    exc = paramiko.SSHException("Server '192.168.1.104' not found in known_hosts")
    jump_error = Exception("Could not connect to jump server 192.168.1.104: " + str(exc))
    jump_error.__cause__ = exc

    assert is_host_key_failure(jump_error) is True


def test_is_host_key_failure_recognizes_bad_host_key_exception():
    class FakeKey:
        def get_base64(self):
            return "AAAAfakekey"

    exc = paramiko.BadHostKeyException("192.168.1.104", FakeKey(), FakeKey())
    jump_error = Exception("Could not connect to jump server 192.168.1.104: " + str(exc))
    jump_error.__cause__ = exc

    assert is_host_key_failure(jump_error) is True


def test_is_host_key_failure_false_for_unrelated_exception():
    auth_error = Exception("Could not connect to jump server 192.168.1.104: Authentication failed.")
    auth_error.__cause__ = paramiko.AuthenticationException("Authentication failed.")

    assert is_host_key_failure(auth_error) is False
