"""Vendor/search filtering rules for the device inventory panel."""

from types import SimpleNamespace

from app.core.device_filter import ALL_VENDORS, filter_options, matches, vendor_family


def _device(name, host, vendor):
    return SimpleNamespace(name=name, host=host, vendor=vendor)


def test_vendor_family_is_the_leading_brand():
    assert vendor_family("Cisco IOS-XE") == "Cisco"
    assert vendor_family("Nokia SR OS") == "Nokia"
    assert vendor_family("Huawei VRP") == "Huawei"


def test_filter_options_offer_all_then_family_groups_then_vendors():
    options = filter_options(["Cisco IOS", "Cisco IOS-XE", "Huawei VRP", "Nokia SR OS", "Nokia SR Linux"])

    assert options == [
        ALL_VENDORS,
        "Cisco (all)", "Cisco IOS", "Cisco IOS-XE",
        "Huawei VRP",
        "Nokia (all)", "Nokia SR OS", "Nokia SR Linux",
    ]


def test_all_vendors_matches_everything():
    assert matches(_device("pe-1", "10.0.0.1", "Nokia SR OS"), ALL_VENDORS, "")


def test_family_option_matches_every_vendor_in_that_family():
    assert matches(_device("core-1", "10.0.0.1", "Cisco IOS-XE"), "Cisco (all)", "")
    assert matches(_device("core-2", "10.0.0.2", "Cisco IOS-XR"), "Cisco (all)", "")
    assert not matches(_device("pe-1", "10.0.0.3", "Nokia SR OS"), "Cisco (all)", "")


def test_specific_vendor_option_matches_only_that_vendor():
    assert matches(_device("core-1", "10.0.0.1", "Cisco IOS-XE"), "Cisco IOS-XE", "")
    assert not matches(_device("core-2", "10.0.0.2", "Cisco IOS-XR"), "Cisco IOS-XE", "")


def test_search_matches_name_or_host_case_insensitively():
    device = _device("POC1-1IOXE", "10.246.222.1", "Cisco IOS-XE")

    assert matches(device, ALL_VENDORS, "poc1")
    assert matches(device, ALL_VENDORS, "246.222")
    assert matches(device, ALL_VENDORS, "  ")
    assert not matches(device, ALL_VENDORS, "sros")


def test_vendor_and_search_must_both_match():
    device = _device("POC1-1SROS", "10.246.111.1", "Nokia SR OS")

    assert not matches(device, "Cisco (all)", "POC1")
