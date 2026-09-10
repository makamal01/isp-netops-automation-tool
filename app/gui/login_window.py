"""Login dialog: handles first-run admin creation, password auth, and MFA."""
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QFormLayout,
    QMessageBox
)

from app.auth.auth_manager import AuthManager
from app.auth import mfa_manager
from app.gui.mfa_window import MfaVerifyDialog, MfaEnrollDialog
from app.utils import audit_log


class LoginWindow(QDialog):
    def __init__(self, auth_manager: AuthManager):
        super().__init__()
        self.auth = auth_manager
        self.authenticated_username = None
        self.first_run = not self.auth.users_exist()

        self.setWindowTitle("ISP NetOps Tool - " + ("Create Admin Account" if self.first_run else "Login"))
        self.setMinimumWidth(360)

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)

        self.confirm_password_edit = None
        if self.first_run:
            self.confirm_password_edit = QLineEdit()
            self.confirm_password_edit.setEchoMode(QLineEdit.Password)
            form.addRow("Confirm Password:", self.confirm_password_edit)

        self.submit_btn = QPushButton("Create Admin Account" if self.first_run else "Login")
        self.submit_btn.clicked.connect(self._on_submit)
        self.password_edit.returnPressed.connect(self._on_submit)

        info = QLabel(
            "No accounts exist yet. Create the first administrator account."
            if self.first_run else
            "Sign in with your ISP NetOps Tool credentials."
        )
        info.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(self.submit_btn)
        self.setLayout(layout)

    def _on_submit(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            QMessageBox.warning(self, "Missing info", "Username and password are required.")
            return

        if self.first_run:
            if password != self.confirm_password_edit.text():
                QMessageBox.warning(self, "Mismatch", "Passwords do not match.")
                return
            if len(password) < 8:
                QMessageBox.warning(self, "Weak password", "Use at least 8 characters.")
                return
            self.auth.create_user(username, password, role="admin")
            self.authenticated_username = username
            QMessageBox.information(self, "Account created", "Admin account created. You can enable MFA next.")
            self._offer_mfa_enrollment(username)
            self.accept()
            return

        remaining_lockout = self.auth.is_locked_out(username)
        if remaining_lockout:
            QMessageBox.critical(
                self, "Account locked",
                f"Too many failed attempts. Try again in {remaining_lockout} minute(s).",
            )
            return

        if not self.auth.verify_password(username, password):
            QMessageBox.critical(self, "Login failed", "Invalid username or password.")
            return

        user = self.auth.get_user(username)
        if user.mfa_enabled:
            secret = self.auth.get_mfa_secret(username)
            verify_dialog = MfaVerifyDialog(secret)
            if verify_dialog.exec() != QDialog.Accepted:
                audit_log.log_event("mfa_failed", username=username)
                QMessageBox.critical(self, "MFA failed", "Invalid or missing authentication code.")
                return
            audit_log.log_event("mfa_verified", username=username)
        else:
            self._offer_mfa_enrollment(username)

        self.authenticated_username = username
        self.accept()

    def _offer_mfa_enrollment(self, username: str):
        choice = QMessageBox.question(
            self, "Enable MFA?",
            "Multi-factor authentication adds an extra layer of security.\n"
            "Enable MFA now using an authenticator app?",
        )
        if choice == QMessageBox.Yes:
            secret = mfa_manager.generate_secret()
            enroll_dialog = MfaEnrollDialog(username, secret)
            if enroll_dialog.exec() == QDialog.Accepted:
                self.auth.enable_mfa(username, secret)
                QMessageBox.information(self, "MFA enabled", "MFA has been enabled for your account.")
