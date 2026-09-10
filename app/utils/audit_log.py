"""Audit logging: append-only, rotating log of security- and change-relevant
events (logins, MFA, device inventory edits, command runs). Separate from
ordinary debug logging so it can be handed to a security/NOC audit process."""
import logging
from logging.handlers import RotatingFileHandler

from app.config import LOG_FILE

_logger = logging.getLogger("isp_netops_audit")
_logger.setLevel(logging.INFO)

if not _logger.handlers:
    handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    _logger.addHandler(handler)


def log_event(action: str, username: str = "-", detail: str = ""):
    message = f"user={username} action={action}"
    if detail:
        message += f" detail={detail}"
    _logger.info(message)
