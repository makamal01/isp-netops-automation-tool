"""Vendor -> Netmiko device_type mapping."""

VENDOR_MAP = {
    "Cisco IOS": "cisco_ios",
    "Cisco IOS-XE": "cisco_xe",
    "Cisco IOS-XR": "cisco_xr",
    "Cisco NX-OS": "cisco_nxos",
    "Huawei VRP": "huawei",
    "Nokia SR OS": "alcatel_sros",
    "Nokia SR Linux": "nokia_srl",
}

VENDOR_NAMES = list(VENDOR_MAP.keys())

# ntc-templates ships no cisco_xe_* templates, but IOS-XE `show` output
# matches the cisco_ios templates, so TextFSM parsing is redirected there.
# Netmiko still uses its own cisco_xe driver for the live connection - this
# mapping only affects which template set is used to parse captured output.
PARSE_PLATFORM_MAP = {
    "cisco_xe": "cisco_ios",
}


def to_netmiko_type(vendor_name: str) -> str:
    """Map the user-facing vendor label to a supported Netmiko driver."""
    try:
        return VENDOR_MAP[vendor_name]
    except KeyError:
        raise ValueError(f"Unsupported vendor: {vendor_name}")


def to_parse_platform(netmiko_device_type: str) -> str:
    """Map a Netmiko device_type to the ntc-templates platform used for
    TextFSM parsing, redirecting types with no template coverage of
    their own to the closest compatible template set."""
    return PARSE_PLATFORM_MAP.get(netmiko_device_type, netmiko_device_type)
