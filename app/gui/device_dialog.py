"""Add/Edit device dialog."""
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox
)

from app.core.vendors import VENDOR_NAMES
from app.core.device_manager import Device, validate_device_fields
from app.core.command_runner import run_commands_on_device, open_jump_transport, JumpServerError
from app.core.host_key_manager import is_host_key_failure
from app.gui.host_key_prompt import offer_host_key_trust
from app.utils import crypto


class DeviceDialog(QDialog):
    def __init__(self, device=None, jump_server_manager=None, username: str = "-"):
        super().__init__()
        self.setWindowTitle("Edit Device" if device else "Add Device")
        self.device = device
        self.jump_server_manager = jump_server_manager
        self.username = username

        self.name_edit = QLineEdit(device.name if device else "")
        self.host_edit = QLineEdit(device.host if device else "")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(device.port if device else 22)
        self.vendor_combo = QComboBox()
        self.vendor_combo.addItems(VENDOR_NAMES)
        if device:
            self.vendor_combo.setCurrentText(device.vendor)
        self.username_edit = QLineEdit(device.username if device else "")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("(unchanged)" if device else "")
        self.secret_edit = QLineEdit()
        self.secret_edit.setEchoMode(QLineEdit.Password)
        self.secret_edit.setPlaceholderText("optional enable/privileged password")

        form = QFormLayout()
        form.addRow("Name:", self.name_edit)
        form.addRow("Host/IP:", self.host_edit)
        form.addRow("Port:", self.port_spin)
        form.addRow("Vendor:", self.vendor_combo)
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)
        form.addRow("Enable/Secret:", self.secret_edit)

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)

        buttons = QHBoxLayout()
        buttons.addWidget(test_btn)
        buttons.addWidget(save_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.result_data = None

    def _current_secret_encrypted(self) -> str:
        if self.secret_edit.text():
            return crypto.encrypt(self.secret_edit.text())
        return self.device.secret_encrypted if self.device else ""

    def _test_connection(self):
        host = self.host_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text() or (self.device.get_password() if self.device else "")
        if not host or not username or not password:
            QMessageBox.warning(self, "Missing info", "Host, username and password are required to test.")
            return

        temp_device = Device(
            name=self.name_edit.text().strip() or "(unnamed)",
            host=host,
            vendor=self.vendor_combo.currentText(),
            username=username,
            password_encrypted=crypto.encrypt(password),
            port=self.port_spin.value(),
            secret_encrypted=self._current_secret_encrypted(),
        )

        jump_client = None
        jump_transport = None
        jump_config = self.jump_server_manager.get_config() if self.jump_server_manager else None
        if jump_config and jump_config.enabled:
            try:
                jump_client = open_jump_transport(jump_config)
                jump_transport = jump_client.get_transport()
            except JumpServerError as exc:
                QMessageBox.critical(self, "JumpServer error", str(exc))
                return

        try:
            if self._connect_offering_host_key_trust(temp_device, jump_transport):
                QMessageBox.information(self, "Success", f"Connected to {host} successfully.")
        finally:
            if jump_client:
                jump_client.close()

    def _connect_offering_host_key_trust(self, device: Device, jump_transport) -> bool:
        """Try the connection; if it fails specifically because the host
        key isn't trusted yet, offer to trust it right here (PuTTY-style)
        and retry once, instead of just failing with a known_hosts error."""
        result = run_commands_on_device(device, [], jump_transport=jump_transport)
        if result.success:
            return True
        if not is_host_key_failure(result.error):
            QMessageBox.critical(self, "Connection failed", result.error)
            return False

        if not offer_host_key_trust(self, device.host, device.port, jump_transport=jump_transport, username=self.username):
            return False

        result = run_commands_on_device(device, [], jump_transport=jump_transport)
        if not result.success:
            QMessageBox.critical(self, "Connection failed", result.error)
            return False
        return True

    def _on_save(self):
        name = self.name_edit.text().strip()
        host = self.host_edit.text().strip()
        username = self.username_edit.text().strip()

        password = self.password_edit.text() or (self.device.get_password() if self.device else "")
        errors = validate_device_fields(name, host, self.vendor_combo.currentText(), username, password, self.port_spin.value())
        if errors:
            QMessageBox.warning(self, "Invalid device", "\n".join(errors))
            return

        self.result_data = {
            "name": name,
            "host": host,
            "port": self.port_spin.value(),
            "vendor": self.vendor_combo.currentText(),
            "username": username,
            "password": self.password_edit.text() or None,
            "secret": self.secret_edit.text() or None,
        }
        self.accept()
