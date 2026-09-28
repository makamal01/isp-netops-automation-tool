"""Vendor/search filtering rules for the device inventory panel."""

from collections import Counter
from typing import Iterable, List, Sequence

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


def selection_summary(checked_devices: Sequence, hidden_count: int) -> str:
    """e.g. "Selected: 12, Cisco IOS-XE 11 · Nokia SR OS 1 (1 hidden by filter)".
    Calling out hidden devices is the point: a checked device the filter
    hides would otherwise be run against without the operator seeing it."""
    if not checked_devices:
        return "Selected: 0"
    counts = Counter(device.vendor for device in checked_devices)
    breakdown = " · ".join(
        f"{vendor} {count}" for vendor, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )
    summary = f"Selected: {len(checked_devices)}, {breakdown}"
    if hidden_count:
        summary += f" ({hidden_count} hidden by filter)"
    return summary
