"""Mocked transport tests for SSH safety and cancellation behavior."""

from threading import Event

from app.core import command_runner
from app.core.command_runner import run_commands_on_device
from app.core.device_manager import Device
from app.utils import crypto


def _device():
    """Create a device with encrypted test credentials and no live dependency."""
    return Device(
        name="lab-router",
        host="192.0.2.1",
        vendor="Cisco IOS",
        username="admin",
        password_encrypted=crypto.encrypt("secret"),
    )


def test_cancelled_device_does_not_open_ssh_connection(monkeypatch):
    called = False

    def connect_handler(**kwargs):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(command_runner, "ConnectHandler", connect_handler)
    cancel_event = Event()
    cancel_event.set()

    result = run_commands_on_device(_device(), ["show version"], cancel_event=cancel_event)

    assert result.success is False
    assert result.error == "Cancelled by operator"
    assert called is False


def test_device_connection_uses_strict_host_key_options(monkeypatch):
    captured = {}

    class FakeConnection:
        device_type = "cisco_ios"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_command(self, command, **kwargs):
            return "Version output"

    def connect_handler(**kwargs):
        captured.update(kwargs)
        return FakeConnection()

    monkeypatch.setattr(command_runner, "ConnectHandler", connect_handler)

    result = run_commands_on_device(_device(), ["show version"])

    assert result.success is True
    assert captured["ssh_strict"] is True
    assert captured["system_host_keys"] is True


def test_missing_host_key_is_not_reported_as_timeout(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            raise command_runner.NetmikoTimeoutException(
                "Server '10.246.111.1' not found in known_hosts"
            )

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(command_runner, "ConnectHandler", lambda **kwargs: FakeConnection())

    result = run_commands_on_device(_device(), ["show version"])

    assert result.success is False
    assert result.error.startswith("SSH host-key error:")
    assert "Connection timed out" not in result.error
    assert "Host Keys > Trust SSH Host Key..." in result.error


def test_host_key_mismatch_points_to_trust_dialog(monkeypatch):
    """A stale/changed key (paramiko.BadHostKeyException, a subclass of
    SSHException) must get the same actionable next step as a missing key,
    not a generic protocol-error message."""
    import paramiko

    class FakeKey:
        def get_base64(self):
            return "AAAAfakekey"

    class FakeConnection:
        def __enter__(self):
            raise paramiko.BadHostKeyException(
                "10.246.111.1", got_key=FakeKey(), expected_key=FakeKey(),
            )

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(command_runner, "ConnectHandler", lambda **kwargs: FakeConnection())

    result = run_commands_on_device(_device(), ["show version"])

    assert result.success is False
    assert result.error.startswith("SSH host-key or protocol error:")
    assert "Host Keys > Trust SSH Host Key..." in result.error


def test_unexpected_driver_error_gets_a_clear_category_prefix(monkeypatch):
    """Every other failure branch has a recognizable prefix; the catch-all
    for anything else must too, instead of showing a bare exception string
    that looks uncategorized next to the others."""
    class FakeConnection:
        def __enter__(self):
            raise ValueError("unsupported vendor driver quirk")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(command_runner, "ConnectHandler", lambda **kwargs: FakeConnection())

    result = run_commands_on_device(_device(), ["show version"])

    assert result.success is False
    assert result.error.startswith("Unexpected error:")
    assert "unsupported vendor driver quirk" in result.error