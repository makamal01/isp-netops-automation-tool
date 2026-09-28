"""Vendor/search filtering rules for the device inventory panel."""

from typing import Iterable, List

from app.core.vendors import VENDOR_NAMES

ALL_VENDORS = "All vendors"
_FAMILY_SUFFIX = " (all)"


def vendor_family(vendor: str) -> str:
    """The brand a vendor label belongs to, e.g. "Cisco IOS-XE" -> "Cisco"."""
    return vendor.split()[0]


def filter_options(vendor_names: Iterable[str] = VENDOR_NAMES) -> List[str]:
    """Dropdown entries: everything, then per brand a "<Brand> (all)" group
    (only when the brand has more than one platform) followed by its platforms."""
    families = {}
    for vendor in vendor_names:
        families.setdefault(vendor_family(vendor), []).append(vendor)
    options = [ALL_VENDORS]
    for family, vendors in families.items():
        if len(vendors) > 1:
            options.append(family + _FAMILY_SUFFIX)
        options.extend(vendors)
    return options


def matches(device, vendor_option: str, search_text: str) -> bool:
    """True when the device passes both the vendor option and the name/IP search."""
    if vendor_option.endswith(_FAMILY_SUFFIX):
        if vendor_family(device.vendor) != vendor_option[: -len(_FAMILY_SUFFIX)]:
            return False
    elif vendor_option != ALL_VENDORS and device.vendor != vendor_option:
        return False
    needle = search_text.strip().lower()
    return not needle or needle in device.name.lower() or needle in device.host.lower()
