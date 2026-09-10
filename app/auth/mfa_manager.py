"""TOTP-based multi-factor authentication (compatible with Google
Authenticator, Microsoft Authenticator, Authy, etc.)."""
import io

import pyotp
import qrcode

from app.config import APP_NAME


def generate_secret() -> str:
    """Create the Base32 seed shared by the app and an authenticator app."""
    return pyotp.random_base32()


def get_provisioning_uri(username: str, secret: str) -> str:
    """Build the standard otpauth URI used to render an enrollment QR code."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=APP_NAME)


def generate_qr_png_bytes(uri: str) -> bytes:
    """Render an otpauth URI as PNG bytes for the Qt enrollment dialog."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def verify_code(secret: str, code: str) -> bool:
    """Verify a TOTP code, allowing one adjacent time step for clock skew."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code.strip(), valid_window=1)
