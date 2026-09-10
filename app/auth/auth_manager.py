"""Local user store: bcrypt password hashing + encrypted MFA secrets.

Users are persisted as JSON in the per-user app-data directory. This is
intentionally simple (no server/db) so the tool stays a single deployable
laptop app. For shared/team deployments, point USERS_FILE at a shared,
access-controlled network path instead.
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict

import bcrypt

from app.config import (
    USERS_FILE, MAX_FAILED_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES,
    StorageError, atomic_write_text,
)
from app.utils import crypto
from app.utils import audit_log


@dataclass
class User:
    username: str
    password_hash: str
    role: str = "engineer"
    mfa_enabled: bool = False
    mfa_secret_encrypted: str = ""
    failed_attempts: int = 0
    locked_until: str = ""  # ISO timestamp, empty if not locked


class AuthManager:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._load()

    def _load(self):
        if USERS_FILE.exists():
            try:
                raw = json.loads(USERS_FILE.read_text(encoding="utf-8-sig"))
                if not isinstance(raw, list):
                    raise ValueError("user store must contain a list")
                self._users = {u["username"]: User(**u) for u in raw}
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise StorageError(f"Could not load user store: {exc}") from exc
        else:
            self._users = {}

    def _save(self):
        atomic_write_text(
            USERS_FILE,
            json.dumps([asdict(u) for u in self._users.values()], indent=2),
        )

    def users_exist(self) -> bool:
        return len(self._users) > 0

    def create_user(self, username: str, password: str, role: str = "engineer") -> User:
        if username in self._users:
            raise ValueError("User already exists")
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = User(username=username, password_hash=pw_hash, role=role)
        self._users[username] = user
        self._save()
        audit_log.log_event("account_created", username=username)
        return user

    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)

    def is_locked_out(self, username: str) -> Optional[int]:
        """Return remaining lockout minutes if the account is locked, else None."""
        user = self._users.get(username)
        if not user or not user.locked_until:
            return None
        locked_until = datetime.fromisoformat(user.locked_until)
        if datetime.now() >= locked_until:
            return None
        return max(1, int((locked_until - datetime.now()).total_seconds() // 60) + 1)

    def verify_password(self, username: str, password: str) -> bool:
        """Check credentials and persist lockout/audit state for every attempt."""
        user = self._users.get(username)
        if not user:
            audit_log.log_event("login_failed", username=username, detail="unknown user")
            return False

        if self.is_locked_out(username):
            audit_log.log_event("login_blocked", username=username, detail="account locked")
            return False

        if bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            user.failed_attempts = 0
            user.locked_until = ""
            self._save()
            audit_log.log_event("login_success", username=username)
            return True

        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
            audit_log.log_event("account_locked", username=username, detail=f"{LOCKOUT_DURATION_MINUTES}min")
        self._save()
        audit_log.log_event("login_failed", username=username, detail=f"attempt {user.failed_attempts}")
        return False

    def set_password(self, username: str, new_password: str):
        user = self._users[username]
        user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        self._save()
        audit_log.log_event("password_changed", username=username)

    def enable_mfa(self, username: str, mfa_secret: str):
        """Encrypt and persist the TOTP seed; the plaintext seed is never stored."""
        user = self._users[username]
        user.mfa_secret_encrypted = crypto.encrypt(mfa_secret)
        user.mfa_enabled = True
        self._save()
        audit_log.log_event("mfa_enabled", username=username)

    def disable_mfa(self, username: str):
        """Remove MFA enrollment and its encrypted seed from the local account."""
        user = self._users[username]
        user.mfa_enabled = False
        user.mfa_secret_encrypted = ""
        self._save()
        audit_log.log_event("mfa_disabled", username=username)

    def get_mfa_secret(self, username: str) -> Optional[str]:
        """Decrypt an enrolled TOTP seed only at the verification boundary."""
        user = self._users.get(username)
        if not user or not user.mfa_secret_encrypted:
            return None
        return crypto.decrypt(user.mfa_secret_encrypted)
