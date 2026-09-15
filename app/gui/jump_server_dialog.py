"""JumpServer configuration dialog."""
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QPushButton,
    QVBoxLayout, QMessageBox, QLabel
)

from app.core.jump_server import JumpServerManager, JumpServerConfig
from app.core.command_runner import open_jump_transport, JumpServerError
from app.core.host_key_manager import is_host_key_failure
from app.gui.host_key_prompt import offer_host_key_trust
from app.utils import crypto


class JumpServerDialog(QDialog):
    def __init__(self, jump_server_manager: JumpServerManager, username: str = "-"):
        super().__init__()
        self.manager = jump_server_manager
        self.username = username
        config = jump_server_manager.get_config()

        self.setWindowTitle("JumpServer Settings")
        self.setMinimumWidth(360)

        info = QLabel(
            "When enabled, all device connections are routed through this "
            "jump server instead of connecting to routers directly. "
            "Each router still uses its own stored credentials."
        )
        info.setWordWrap(True)

        self.enabled_checkbox = QCheckBox("Route device connections through jump server")
        self.enabled_checkbox.setChecked(config.enabled)

        self.host_edit = QLineEdit(config.host)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(config.port)
        self.username_edit = QLineEdit(config.username)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("(unchanged)" if config.password_encrypted else "")

        form = QFormLayout()
        form.addRow("Host/IP:", self.host_edit)
        form.addRow("Port:", self.port_spin)
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.enabled_checkbox)
        layout.addLayout(form)
        layout.addWidget(test_btn)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def _current_password(self) -> str:
        return self.password_edit.text() or self.manager.get_config().get_password()

    def _test_connection(self):
        host = self.host_edit.text().strip()
        username = self.username_edit.text().strip()
        if not host or not username or not self._current_password():
            QMessageBox.warning(self, "Missing info", "Host, username and password are required to test.")
            return
        test_config = JumpServerConfig(
            enabled=True, host=host, port=self.port_spin.value(), username=username,
            password_encrypted=crypto.encrypt(self._current_password()),
        )
        if not self._connect_offering_host_key_trust(test_config):
            return
        QMessageBox.information(self, "Success", "Connected to jump server successfully.")

    def _connect_offering_host_key_trust(self, test_config: JumpServerConfig) -> bool:
        """Try the connection; if it fails specifically because the host
        key isn't trusted yet, offer to trust it right here (PuTTY-style)
        and retry once, instead of just failing with a known_hosts error."""
        try:
            client = open_jump_transport(test_config)
            client.close()
            return True
        except JumpServerError as exc:
            if not is_host_key_failure(exc):
                QMessageBox.critical(self, "Connection failed", str(exc))
                return False

        if not offer_host_key_trust(self, test_config.host, test_config.port, username=self.username):
            return False

        try:
            client = open_jump_transport(test_config)
            client.close()
            return True
        except JumpServerError as exc:
            QMessageBox.critical(self, "Connection failed", str(exc))
            return False

    def _on_save(self):
        host = self.host_edit.text().strip()
        username = self.username_edit.text().strip()
        if self.enabled_checkbox.isChecked() and not (host and username):
            QMessageBox.warning(self, "Missing info", "Host and username are required to enable the jump server.")
            return
        self.manager.save(
            enabled=self.enabled_checkbox.isChecked(),
            host=host,
            port=self.port_spin.value(),
            username=username,
            password=self.password_edit.text() or None,
        )
        self.accept()
