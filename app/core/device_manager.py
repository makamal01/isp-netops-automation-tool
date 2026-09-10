"""Device inventory persistence (YAML) with encrypted credentials at rest."""
import csv
import ipaddress
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

import yaml

from app.config import DEVICES_FILE, StorageError, atomic_write_text
from app.core.vendors import VENDOR_NAMES
from app.utils import crypto

REQUIRED_CSV_COLUMNS = ("name", "host", "vendor", "username", "password")
CSV_COLUMNS = REQUIRED_CSV_COLUMNS + ("port", "secret")
_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,253}[A-Za-z0-9])?$")


def validate_device_fields(
    name: str,
    host: str,
    vendor: str,
    username: str,
    password: str,
    port: int,
    existing_names=None,
):
    errors = []
    if not name or len(name) > 128:
        errors.append("Device name is required and must be 128 characters or fewer.")
    if existing_names and name in existing_names:
        errors.append(f"Device name '{name}' already exists.")
    if not host or len(host) > 253:
        errors.append("Host is required and must be 253 characters or fewer.")
    else:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if not _HOSTNAME_RE.fullmatch(host):
                errors.append("Host must be a valid IP address or hostname.")
    if vendor not in VENDOR_NAMES:
        errors.append(f"Unsupported vendor: {vendor or '(empty)'}.")
    if not username or len(username) > 128:
        errors.append("Username is required and must be 128 characters or fewer.")
    if not password:
        errors.append("Password is required.")
    if not 1 <= port <= 65535:
        errors.append("Port must be between 1 and 65535.")
    return errors


@dataclass
class Device:
    name: str
    host: str
    vendor: str
    username: str
    password_encrypted: str
    port: int = 22
    secret_encrypted: str = ""  # enable/privileged-mode password, if needed

    def get_password(self) -> str:
        return crypto.decrypt(self.password_encrypted)

    def get_secret(self) -> str:
        return crypto.decrypt(self.secret_encrypted) if self.secret_encrypted else ""


class DeviceManager:
    def __init__(self):
        self.devices: List[Device] = []
        self._load()

    def _load(self):
        if DEVICES_FILE.exists():
            try:
                raw = yaml.safe_load(DEVICES_FILE.read_text(encoding="utf-8")) or []
                if not isinstance(raw, list):
                    raise ValueError("device store must contain a list")
                self.devices = [Device(**d) for d in raw]
            except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
                raise StorageError(f"Could not load device inventory: {exc}") from exc
        else:
            self.devices = []

    def _save(self):
        atomic_write_text(
            DEVICES_FILE,
            yaml.safe_dump([asdict(d) for d in self.devices], sort_keys=False),
        )

    def list_devices(self) -> List[Device]:
        return list(self.devices)

    def add_device(self, name, host, vendor, username, password, port=22, secret=""):
        errors = validate_device_fields(
            name, host, vendor, username, password, port,
            existing_names={device.name for device in self.devices},
        )
        if errors:
            raise ValueError(" ".join(errors))
        device = Device(
            name=name,
            host=host,
            vendor=vendor,
            username=username,
            password_encrypted=crypto.encrypt(password),
            port=port,
            secret_encrypted=crypto.encrypt(secret) if secret else "",
        )
        self.devices.append(device)
        self._save()
        return device

    def update_device(self, index: int, **kwargs):
        device = self.devices[index]
        if "password" in kwargs:
            device.password_encrypted = crypto.encrypt(kwargs.pop("password"))
        if "secret" in kwargs:
            secret = kwargs.pop("secret")
            device.secret_encrypted = crypto.encrypt(secret) if secret else ""
        for k, v in kwargs.items():
            setattr(device, k, v)
        self._save()

    def remove_device(self, index: int):
        del self.devices[index]
        self._save()

    @staticmethod
    def write_csv_template(path: str):
        """Write a header-only template that can be opened in spreadsheet apps."""
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            csv.writer(file).writerow(CSV_COLUMNS)

    def import_from_csv(self, path: str) -> Tuple[int, List[str]]:
        """Bulk-add devices from a CSV file.

        Expected columns: name, host, vendor, username, password
        Optional columns: port, secret
        Returns (added_count, error_messages) - malformed rows are skipped
        and reported, valid rows are still imported.
        """
        errors: List[str] = []
        added = 0
        imported_names = set()
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            missing = [c for c in REQUIRED_CSV_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                errors.append(f"Missing required column(s): {', '.join(missing)}")
                return 0, errors

            for row_num, row in enumerate(reader, start=2):
                name = (row.get("name") or "").strip()
                host = (row.get("host") or "").strip()
                vendor = (row.get("vendor") or "").strip()
                username = (row.get("username") or "").strip()
                password = row.get("password") or ""

                port_raw = (row.get("port") or "22").strip()
                try:
                    port = int(port_raw)
                except ValueError:
                    errors.append(f"Row {row_num}: invalid port '{port_raw}', skipped")
                    continue

                row_errors = validate_device_fields(
                    name, host, vendor, username, password, port,
                    existing_names={device.name for device in self.devices} | imported_names,
                )
                if row_errors:
                    errors.append(f"Row {row_num}: {' '.join(row_errors)} Skipped.")
                    continue
                self.add_device(name, host, vendor, username, password, port, (row.get("secret") or "").strip())
                imported_names.add(name)
                added += 1
        return added, errors

    def find_by_name(self, name: str) -> Optional[Device]:
        return next((d for d in self.devices if d.name == name), None)
