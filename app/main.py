"""Entry point for the ISP NetOps Tool desktop application."""
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.auth.auth_manager import AuthManager
from app.gui.login_window import LoginWindow
from app.gui.main_window import MainWindow
from app.config import StorageError


def main():
    app = QApplication(sys.argv)
    try:
        auth_manager = AuthManager()

        login = LoginWindow(auth_manager)
        if login.exec() != LoginWindow.Accepted:
            sys.exit(0)

        window = MainWindow(auth_manager, login.authenticated_username)
        window.show()
        sys.exit(app.exec())
    except StorageError as exc:
        QMessageBox.critical(app.activeWindow(), "Local data error", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
