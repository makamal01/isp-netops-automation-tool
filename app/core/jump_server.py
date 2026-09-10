"""Optional SSH jump/bastion host configuration. When enabled, device
connections are tunnelled through this host (login to the jump server,
open a proxied channel per router) instead of connecting to routers
directly from this machine. Each router still authenticates with its own
credentials from the device inventory - the jump server only provides
network reachability."""
from dataclasses import dataclass, asdict
from typing import Optional

import yaml

from app.config import JUMPSERVER_FILE, StorageError, atomic_write_text
from app.utils import crypto


@dataclass
class JumpServerConfig:
    enabled: bool = False
    host: str = ""
    port: int = 22
    username: str = ""
    password_encrypted: str = ""

    def get_password(self) -> str:
        return crypto.decrypt(self.password_encrypted) if self.password_encrypted else ""


class JumpServerManager:
    def __init__(self):
        self.config = JumpServerConfig()
        self._load()

    def _load(self):
        if JUMPSERVER_FILE.exists():
            try:
                raw = yaml.safe_load(JUMPSERVER_FILE.read_text(encoding="utf-8")) or {}
                if not isinstance(raw, dict):
                    raise ValueError("jump-server store must contain an object")
                self.config = JumpServerConfig(**raw)
            except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
                raise StorageError(f"Could not load jump-server configuration: {exc}") from exc

    def _save(self):
        atomic_write_text(JUMPSERVER_FILE, yaml.safe_dump(asdict(self.config)))

    def get_config(self) -> JumpServerConfig:
        return self.config

    def save(self, enabled: bool, host: str, port: int, username: str, password: Optional[str]):
        """Persist settings; ``password=None`` intentionally retains the stored secret."""
        self.config.enabled = enabled
        self.config.host = host
        self.config.port = port
        self.config.username = username
        if password:
            self.config.password_encrypted = crypto.encrypt(password)
        self._save()
