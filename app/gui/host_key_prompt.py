"""Shared PuTTY-style host-key trust prompt: fetch a host's presented key
and let the operator trust it right at the point of connecting, instead of
requiring a separate trip to Host Keys > Trust SSH Host Key... first.

Used wherever the app first connects to a host - JumpServer Test
Connection, device Test Connection, and any future connect path.
"""
from PySide6.QtWidgets import QMessageBox

from app.core.host_key_manager import fetch_host_key
from app.core.host_key_manager import trust_host_key as _trust_host_key
from app.utils import audit_log


def offer_host_key_trust(parent, host: str, port: int = 22, jump_transport=None, username: str = "-") -> bool:
    """Fetch `host`'s presented key and ask the operator to trust it.

    Returns True if the key is now trusted (the caller should retry its
    connection) or False if the fetch failed or the operator cancelled.
    """
    try:
        info = fetch_host_key(host, port=port, jump_transport=jump_transport)
    except Exception as exc:  # noqa: BLE001 - surface any transport/negotiation error
        QMessageBox.critical(parent, "Could not fetch host key", f"Could not retrieve the host key for {host}: {exc}")
        return False

    box = QMessageBox(parent)
    box.setWindowTitle("Host key not trusted")
    box.setIcon(QMessageBox.Warning)
    box.setText(f"The host key for {host} is not yet trusted by this app.")
    box.setInformativeText(
        f"Key type: {info.key_type}\n"
        f"Fingerprint: {info.fingerprint}\n\n"
        "Verify this matches the device's own key through an approved "
        "out-of-band channel (device CLI, change ticket, network owner) "
        "before trusting it."
    )
    trust_btn = box.addButton("Trust and Continue", QMessageBox.AcceptRole)
    box.addButton("Cancel", QMessageBox.RejectRole)
    box.exec()

    if box.clickedButton() is not trust_btn:
        return False

    _trust_host_key(info)
    audit_log.log_event(
        "host_key_trusted", username=username,
        detail=f"host={info.host} type={info.key_type} fingerprint={info.fingerprint}",
    )
    return True
