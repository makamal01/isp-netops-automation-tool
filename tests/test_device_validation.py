from app.core.device_manager import validate_device_fields


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