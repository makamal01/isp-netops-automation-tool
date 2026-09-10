import pytest
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QTextEdit

from app.core.command_runner import DeviceResult
from app.gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _build_window(device_name, result, qapp):
    window = MainWindow.__new__(MainWindow)
    window.results_table = QTableWidget(1, 3)
    window.results_table.setItem(0, 0, QTableWidgetItem(device_name))
    window.output_view = QTextEdit()
    window.results_by_device = {device_name: result}
    window.results_table.setCurrentCell(0, 0)
    return window


def test_output_view_shows_successful_device_output(qapp):
    result = DeviceResult(
        device_name="lab-router",
        host="192.0.2.1",
        success=True,
        output="--- show version ---\nIOS-XE test",
        duration_seconds=0.1,
    )
    window = _build_window("lab-router", result, qapp)

    window._on_result_row_selected()

    assert window.output_view.toPlainText() == "--- show version ---\nIOS-XE test"


def test_output_view_shows_failed_device_error(qapp):
    result = DeviceResult(
        device_name="offline-router",
        host="192.0.2.2",
        success=False,
        output="",
        duration_seconds=0.1,
        error="Connection timed out",
    )
    window = _build_window("offline-router", result, qapp)

    window._on_result_row_selected()

    assert window.output_view.toPlainText() == "Connection timed out"


def test_first_result_is_shown_without_manual_row_selection(qapp):
    window = MainWindow.__new__(MainWindow)
    window.results_table = QTableWidget(0, 3)
    window.output_view = QTextEdit()
    window.results_by_device = {}
    result = DeviceResult(
        device_name="lab-router",
        host="192.0.2.1",
        success=True,
        output="--- show version ---\nIOS-XE test",
        duration_seconds=0.1,
    )

    window._on_device_result(result)

    assert window.output_view.toPlainText() == "--- show version ---\nIOS-XE test"