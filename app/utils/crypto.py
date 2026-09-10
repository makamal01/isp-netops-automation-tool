"""Symmetric encryption helpers used to protect stored secrets (device
passwords, MFA seeds) at rest on the local machine.
"""
import os
import stat

from cryptography.fernet import Fernet

from app.config import KEY_FILE


def _load_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    try:
        os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass  # best-effort on platforms where chmod semantics differ (e.g. Windows)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    if not token:
        return ""
    return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
