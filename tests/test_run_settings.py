"""Concurrency/timeout must be operator-adjustable in the GUI, not hardcoded
literals baked into the run handler."""

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

from app.config import DEFAULT_MAX_WORKERS, DEFAULT_SSH_TIMEOUT
from app.core.deployment_policy import DeploymentPolicy
from app.gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def test_run_controls_default_to_config_values(qapp):
    # Bypass MainWindow.__init__ (it constructs DeviceManager/AuthManager
    # and touches real app-data files) while still running the native
    # QMainWindow.__init__ that setCentralWidget() requires.
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.deployment_policy = DeploymentPolicy()

    window._build_central_widget()

    assert window.max_workers_spin.value() == DEFAULT_MAX_WORKERS
    assert window.timeout_spin.value() == DEFAULT_SSH_TIMEOUT
    assert window.max_workers_spin.minimum() >= 1
    assert window.timeout_spin.minimum() >= 1
