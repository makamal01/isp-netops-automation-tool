"""TOTP-based multi-factor authentication (compatible with Google
Authenticator, Microsoft Authenticator, Authy, etc.)."""
import io

import pyotp
import qrcode

from app.config import APP_NAME


def generate_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(username: str, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=APP_NAME)


def generate_qr_png_bytes(uri: str) -> bytes:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def verify_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code.strip(), valid_window=1)
