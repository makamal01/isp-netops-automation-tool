"""Regression tests for starting a fresh run from the real Run button,
over results left behind by a previous run."""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem

from app.core.command_runner import DeviceResult
from app.core.deployment_policy import DeploymentPolicy
from app.gui import main_window as main_window_module
from app.gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _device(name):
    device = MagicMock()
    device.name = name
    device.host = "192.0.2.1"
    device.vendor = "Cisco IOS-XE"
    return device


def _build_window_with_previous_run(device_names):
    """Real central widget (so buttons carry their real signal wiring),
    holding one completed run's results for the first device."""
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.deployment_policy = DeploymentPolicy()
    window.username = "tester"
    window.results_by_device = {}
    window.cancel_event = None
    window._build_central_widget()

    devices = [_device(name) for name in device_names]
    window.device_manager = MagicMock()
    window.device_manager.list_devices.return_value = devices
    window.jump_server_manager = MagicMock()
    window.jump_server_manager.get_config.return_value.enabled = True
    window._refresh_device_list()
    window.command_edit.setPlainText("show version")

    previous = DeviceResult(
        device_name=device_names[0], host="192.0.2.1", success=True,
        output="PREVIOUS OUTPUT", duration_seconds=0.1,
    )
    window.results_by_device[previous.device_name] = previous
    window.results_table.insertRow(0)
    window.results_table.setItem(0, 0, QTableWidgetItem(previous.device_name))
    window.results_table.setItem(0, 1, QTableWidgetItem("OK"))
    window.results_table.setCurrentCell(0, 0)
    window.output_view.setPlainText("PREVIOUS OUTPUT")
    window.status_label.setText("Done. 1/1 devices succeeded.")
    window.export_btn.setEnabled(True)
    return window


@pytest.fixture
def no_worker_thread():
    with patch.object(main_window_module, "QThread", MagicMock()), \
         patch.object(main_window_module, "BulkRunner", MagicMock()), \
         patch.object(main_window_module, "audit_log", MagicMock()):
        yield


def test_second_run_from_run_button_starts_fresh(qapp, no_worker_thread):
    """Clicking Run again (e.g. after checking another device) must clear the
    previous run's rows and output, not keep showing stale results."""
    window = _build_window_with_previous_run(["core-1", "edge-1"])
    window._set_all_checked(True)

    window.run_btn.click()

    assert window.results_table.rowCount() == 0
    assert window.results_by_device == {}
    assert window.output_view.toPlainText() == ""
    assert window.status_label.text().startswith("Running 1 command(s) on 2 device(s)")
    assert window.run_btn.isEnabled() is False

