"""In-app SSH host-key enrollment: fetch a host's presented key, show its
fingerprint, and let the operator explicitly confirm trust before the app
will use it for real connections."""
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout,
)

from app.core.command_runner import JumpServerError, open_jump_transport
from app.core.host_key_manager import HostKeyInfo, fetch_host_key, trust_host_key
from app.utils import audit_log


class HostKeyDialog(QDialog):
    def __init__(self, jump_server_manager=None, username: str = "-", parent=None):
        super().__init__(parent)
        self.jump_server_manager = jump_server_manager
        self.username = username
        self.fetched_key: HostKeyInfo | None = None

        self.setWindowTitle("Trust SSH Host Key")
        self.setMinimumWidth(420)

        info = QLabel(
            "Fetches the key a host presents during the SSH handshake, without "
            "logging in. Verify the fingerprint through an approved out-of-band "
            "channel (device CLI, change ticket, network owner) before trusting "
            "it - an unexpected change is a security event, not just an error to "
            "click past."
        )
        info.setWordWrap(True)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("10.0.0.1")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)

        jump_config = self.jump_server_manager.get_config() if self.jump_server_manager else None
        self.via_jump_checkbox = QCheckBox("Fetch through configured JumpServer")
        self.via_jump_checkbox.setChecked(bool(jump_config and jump_config.enabled))
        self.via_jump_checkbox.setEnabled(bool(jump_config and jump_config.enabled))

        form = QFormLayout()
        form.addRow("Host/IP:", self.host_edit)
        form.addRow("Port:", self.port_spin)

        self.result_label = QLabel("No key fetched yet.")
        self.result_label.setWordWrap(True)

        fetch_btn = QPushButton("Fetch Key")
        fetch_btn.clicked.connect(self._fetch_key)

        self.trust_btn = QPushButton("Trust and Save")
        self.trust_btn.setEnabled(False)
        self.trust_btn.clicked.connect(self._trust_key)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(self.via_jump_checkbox)
        layout.addWidget(fetch_btn)
        layout.addWidget(self.result_label)
        layout.addWidget(self.trust_btn)
        layout.addWidget(close_btn)
        self.setLayout(layout)

    def _fetch_key(self):
        host = self.host_edit.text().strip()
        if not host:
            QMessageBox.warning(self, "Missing host", "Enter a host or IP address to fetch.")
            return

        self.fetched_key = None
        self.trust_btn.setEnabled(False)
        jump_client = None
        try:
            jump_transport = None
            if self.via_jump_checkbox.isChecked():
                jump_config = self.jump_server_manager.get_config()
                jump_client = open_jump_transport(jump_config)
                jump_transport = jump_client.get_transport()
            self.fetched_key = fetch_host_key(
                host, port=self.port_spin.value(), jump_transport=jump_transport,
            )
        except JumpServerError as exc:
            QMessageBox.critical(self, "JumpServer error", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - surface any transport/negotiation error
            QMessageBox.critical(self, "Fetch failed", f"Could not fetch the host key: {exc}")
            return
        finally:
            if jump_client:
                jump_client.close()

        self.result_label.setText(
            f"Key type: {self.fetched_key.key_type}\n"
            f"Fingerprint: {self.fetched_key.fingerprint}\n\n"
            "Confirm this matches the device's own key before trusting it."
        )
        self.trust_btn.setEnabled(True)

    def _trust_key(self):
        if not self.fetched_key:
            return
        confirm = QMessageBox.question(
            self, "Confirm trust",
            f"Trust this key for {self.fetched_key.host}?\n\n"
            f"Fingerprint: {self.fetched_key.fingerprint}\n\n"
            "Only confirm if you have verified this out-of-band.",
        )
        if confirm != QMessageBox.Yes:
            return
        trust_host_key(self.fetched_key)
        audit_log.log_event(
            "host_key_trusted", username=self.username,
            detail=f"host={self.fetched_key.host} type={self.fetched_key.key_type} fingerprint={self.fetched_key.fingerprint}",
        )
        QMessageBox.information(self, "Key trusted", f"The key for {self.fetched_key.host} is now trusted.")
        self.accept()
