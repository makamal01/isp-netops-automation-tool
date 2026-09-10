"""MFA enrollment (QR code) and verification dialogs."""
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from app.auth import mfa_manager


class MfaEnrollDialog(QDialog):
    def __init__(self, username: str, secret: str):
        super().__init__()
        self.secret = secret
        self.setWindowTitle("Set up MFA")

        uri = mfa_manager.get_provisioning_uri(username, secret)
        png_bytes = mfa_manager.generate_qr_png_bytes(uri)
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes, "PNG")

        qr_label = QLabel()
        qr_label.setPixmap(pixmap.scaled(220, 220, Qt.KeepAspectRatio))

        instructions = QLabel(
            "Scan this QR code with Google Authenticator, Microsoft Authenticator,\n"
            "or Authy, then enter the 6-digit code below to confirm."
        )
        instructions.setWordWrap(True)

        secret_label = QLabel(f"Manual entry key: {secret}")
        secret_label.setWordWrap(True)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("6-digit code")
        self.code_edit.returnPressed.connect(self._verify)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.clicked.connect(self._verify)

        layout = QVBoxLayout()
        layout.addWidget(instructions)
        layout.addWidget(qr_label, alignment=Qt.AlignCenter)
        layout.addWidget(secret_label)
        layout.addWidget(self.code_edit)
        layout.addWidget(confirm_btn)
        self.setLayout(layout)

    def _verify(self):
        if mfa_manager.verify_code(self.secret, self.code_edit.text()):
            self.accept()
        else:
            QMessageBox.critical(self, "Invalid code", "That code did not verify. Try again.")


class MfaVerifyDialog(QDialog):
    def __init__(self, secret: str):
        super().__init__()
        self.secret = secret
        self.setWindowTitle("Two-Factor Authentication")

        label = QLabel("Enter the 6-digit code from your authenticator app:")
        self.code_edit = QLineEdit()
        self.code_edit.returnPressed.connect(self._verify)

        submit_btn = QPushButton("Verify")
        submit_btn.clicked.connect(self._verify)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.code_edit)
        layout.addWidget(submit_btn)
        self.setLayout(layout)

    def _verify(self):
        if mfa_manager.verify_code(self.secret, self.code_edit.text()):
            self.accept()
        else:
            QMessageBox.critical(self, "Invalid code", "That code did not verify. Try again.")
            self.reject()
