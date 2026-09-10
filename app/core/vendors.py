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


def to_netmiko_type(vendor_name: str) -> str:
    """Map the user-facing vendor label to a supported Netmiko driver."""
    try:
        return VENDOR_MAP[vendor_name]
    except KeyError:
        raise ValueError(f"Unsupported vendor: {vendor_name}")
