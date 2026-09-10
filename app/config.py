"""Application-wide configuration and path constants."""
import os
from pathlib import Path

APP_NAME = "ISP NetOps Tool"


class StorageError(Exception):
    """Raised when local application data cannot be safely loaded or saved."""


def get_app_data_dir() -> Path:
    """Return (and create) the per-user directory used to store app data
    (users, device inventory, encryption key). Keeping this outside the
    installed/portable app folder means the exe can be replaced/updated
    without losing local data."""
    base = os.getenv("APPDATA") or str(Path.home())
    app_dir = Path(base) / "ISPNetOpsTool"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def atomic_write_text(path: Path, content: str):
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


APP_DATA_DIR = get_app_data_dir()
USERS_FILE = APP_DATA_DIR / "users.json"
DEVICES_FILE = APP_DATA_DIR / "devices.yaml"
JUMPSERVER_FILE = APP_DATA_DIR / "jumpserver.yaml"
KEY_FILE = APP_DATA_DIR / "secret.key"
KNOWN_HOSTS_FILE = APP_DATA_DIR / "known_hosts"
LOG_FILE = APP_DATA_DIR / "isp_netops_tool.log"

REPORTS_DIR = APP_DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SSH_TIMEOUT = 15
DEFAULT_MAX_WORKERS = 20

# Login lockout policy
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
