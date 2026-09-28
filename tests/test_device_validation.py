import pytest

from app.core import device_manager as device_manager_module
from app.core.device_manager import Device, DeviceManager, validate_device_fields


def test_device_validation_accepts_ip_and_hostname():
    assert validate_device_fields(
        "core-rtr-01", "10.0.0.1", "Cisco IOS", "admin", "secret", 22,
    ) == []
    assert validate_device_fields(
        "edge-rtr-01", "edge.example.net", "Huawei VRP", "admin", "secret", 2222,
    ) == []


def test_device_validation_rejects_invalid_inventory_fields():
    errors = validate_device_fields(
        "", "not a host", "Unknown Vendor", "", "", 70000,
    )

    assert any("Device name is required" in error for error in errors)
    assert any("valid IP address or hostname" in error for error in errors)
    assert any("Unsupported vendor" in error for error in errors)
    assert any("Username is required" in error for error in errors)
    assert any("Password is required" in error for error in errors)
    assert any("between 1 and 65535" in error for error in errors)


def test_device_validation_rejects_duplicate_names():
    errors = validate_device_fields(
        "core-rtr-01", "10.0.0.2", "Cisco IOS", "admin", "secret", 22,
        existing_names={"core-rtr-01"},
    )

    assert errors == ["Device name 'core-rtr-01' already exists."]


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """In-memory inventory writing to a temp file, bypassing the real store."""
    monkeypatch.setattr(device_manager_module, "DEVICES_FILE", tmp_path / "devices.yaml")
    manager = DeviceManager.__new__(DeviceManager)
    manager.devices = [
        Device(name="core-1", host="10.0.0.1", vendor="Cisco IOS-XE", username="admin", password_encrypted="x"),
        Device(name="pe-1", host="10.0.0.2", vendor="Nokia SR OS", username="admin", password_encrypted="x"),
    ]
    return manager


def test_update_rejects_renaming_to_another_devices_name(manager):
    with pytest.raises(ValueError, match="Device name 'core-1' already exists."):
        manager.update_device(1, name="core-1", host="10.9.9.9")

    assert [(d.name, d.host) for d in manager.devices] == [("core-1", "10.0.0.1"), ("pe-1", "10.0.0.2")]
    assert not device_manager_module.DEVICES_FILE.exists()


def test_update_allows_keeping_the_same_name(manager):
    manager.update_device(1, name="pe-1", host="10.0.0.22")

    assert manager.devices[1].host == "10.0.0.22"


def test_update_allows_renaming_to_an_unused_name(manager):
    manager.update_device(1, name="pe-2")

    assert manager.devices[1].name == "pe-2"
