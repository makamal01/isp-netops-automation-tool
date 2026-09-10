"""Add/Edit device dialog."""
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QPushButton,
    QVBoxLayout, QMessageBox
)

from app.core.vendors import VENDOR_NAMES
from app.core.device_manager import validate_device_fields


class DeviceDialog(QDialog):
    def __init__(self, device=None):
        super().__init__()
        self.setWindowTitle("Edit Device" if device else "Add Device")
        self.device = device

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

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(save_btn)
        self.setLayout(layout)

        self.result_data = None

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
