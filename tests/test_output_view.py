"""Regression tests for result-row selection and Output-pane rendering."""

import pytest
from PySide6.QtWidgets import (
    QApplication, QLabel, QProgressBar, QTableWidget, QTableWidgetItem, QTextEdit,
)

from app.core.command_runner import DeviceResult
from app.gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _build_window(device_name, result, qapp):
    """Build the minimal Qt object graph needed without running full MainWindow setup."""
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


def _build_run_window(total):
    window = MainWindow.__new__(MainWindow)
    window.results_table = QTableWidget(0, 3)
    window.output_view = QTextEdit()
    window.results_by_device = {}
    window.status_label = QLabel()
    window.progress_bar = QProgressBar()
    window.run_total = total
    window.run_completed = 0
    window.run_success = 0
    window.progress_bar.setMaximum(total)
    window.progress_bar.setValue(0)
    return window


def test_first_result_is_shown_without_manual_row_selection(qapp):
    window = _build_run_window(total=1)
    result = DeviceResult(
        device_name="lab-router",
        host="192.0.2.1",
        success=True,
        output="--- show version ---\nIOS-XE test",
        duration_seconds=0.1,
    )

    window._on_device_result(result)

    assert window.output_view.toPlainText() == "--- show version ---\nIOS-XE test"


def test_device_result_advances_progress_bar_and_status_text(qapp):
    window = _build_run_window(total=3)

    window._on_device_result(DeviceResult(
        device_name="core-1", host="192.0.2.1", success=True,
        output="ok", duration_seconds=0.1,
    ))
    window._on_device_result(DeviceResult(
        device_name="edge-1", host="192.0.2.2", success=False,
        output="", duration_seconds=0.1, error="Connection timed out",
    ))

    assert window.progress_bar.maximum() == 3
    assert window.progress_bar.value() == 2
    status_text = window.status_label.text()
    assert "2/3" in status_text
    assert "1 succeeded" in status_text
    assert "1 failed" in status_text


def _row_device_names(table):
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def test_clear_rows_for_devices_only_removes_named_devices(qapp):
    """Retrying failed devices must not discard evidence already collected
    for devices that succeeded in the same run."""
    ok_result = DeviceResult(
        device_name="core-1", host="192.0.2.1", success=True,
        output="--- show version ---\nOK", duration_seconds=0.1,
    )
    failed_result = DeviceResult(
        device_name="edge-1", host="192.0.2.2", success=False,
        output="", duration_seconds=0.1, error="Connection timed out",
    )
    window = MainWindow.__new__(MainWindow)
    window.results_table = QTableWidget(2, 3)
    window.results_table.setItem(0, 0, QTableWidgetItem("core-1"))
    window.results_table.setItem(1, 0, QTableWidgetItem("edge-1"))
    window.results_by_device = {"core-1": ok_result, "edge-1": failed_result}

    window._clear_rows_for_devices({"edge-1"})

    assert _row_device_names(window.results_table) == ["core-1"]
    assert window.results_by_device == {"core-1": ok_result}