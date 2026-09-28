"""Regression tests for starting a fresh run and resetting run state from
the real buttons, over results left behind by a previous run."""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem

from app.core.command_runner import DeviceResult
from app.core.deployment_policy import DeploymentPolicy
from app.gui import main_window as main_window_module
from app.gui.main_window import RUN_ALL_VENDORS, MainWindow


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _device(name, vendor="Cisco IOS-XE"):
    device = MagicMock()
    device.name = name
    device.host = "192.0.2.1"
    device.vendor = vendor
    return device


def _build_window_with_previous_run(device_names, vendors=None):
    """Real central widget (so buttons carry their real signal wiring),
    holding one completed run's results for the first device."""
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.deployment_policy = DeploymentPolicy()
    window.username = "tester"
    window.results_by_device = {}
    window.cancel_event = None
    window._build_central_widget()

    vendors = vendors or {}
    devices = [_device(name, vendors.get(name, "Cisco IOS-XE")) for name in device_names]
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
    """Stub out the worker thread; yields the BulkRunner mock so tests can
    see which devices a run was started with."""
    runner = MagicMock()
    with patch.object(main_window_module, "QThread", MagicMock()), \
         patch.object(main_window_module, "BulkRunner", runner), \
         patch.object(main_window_module, "audit_log", MagicMock()):
        yield runner


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


def test_reset_button_clears_previous_run_state(qapp):
    window = _build_window_with_previous_run(["core-1"])
    window.retry_btn.setEnabled(True)

    window.reset_btn.click()

    assert window.results_table.rowCount() == 0
    assert window.results_by_device == {}
    assert window.output_view.toPlainText() == ""
    assert window.status_label.text() == "Idle."
    assert window.export_btn.isEnabled() is False
    assert window.retry_btn.isEnabled() is False


def test_reset_is_disabled_while_a_run_is_in_progress(qapp, no_worker_thread):
    window = _build_window_with_previous_run(["core-1"])
    window.device_list.item(0).setCheckState(Qt.Checked)

    window.run_btn.click()
    assert window.reset_btn.isEnabled() is False

    window._on_run_finished([])
    assert window.reset_btn.isEnabled() is True


MIXED = {"core-1": "Cisco IOS-XE", "core-2": "Cisco IOS-XR", "pe-1": "Nokia SR OS"}


def _run_device_names(runner):
    return [device.name for device in runner.call_args.args[0]]


def _mixed_window():
    window = _build_window_with_previous_run(["core-1", "core-2", "pe-1"], vendors=MIXED)
    window._set_all_checked(True)
    return window


def test_mixed_vendor_run_can_be_narrowed_to_one_brand(qapp, no_worker_thread):
    window = _mixed_window()
    window._ask_mixed_vendor_choice = MagicMock(return_value="Cisco")

    window.run_btn.click()

    assert _run_device_names(no_worker_thread) == ["core-1", "core-2"]
    assert window.device_list.item(2).checkState() == Qt.Unchecked


def test_mixed_vendor_run_can_proceed_on_all(qapp, no_worker_thread):
    window = _mixed_window()
    window._ask_mixed_vendor_choice = MagicMock(return_value=RUN_ALL_VENDORS)

    window.run_btn.click()

    assert _run_device_names(no_worker_thread) == ["core-1", "core-2", "pe-1"]


def test_cancelling_the_mixed_vendor_prompt_changes_nothing(qapp, no_worker_thread):
    window = _mixed_window()
    window._ask_mixed_vendor_choice = MagicMock(return_value=None)

    window.run_btn.click()

    no_worker_thread.assert_not_called()
    assert window.run_btn.isEnabled() is True
    assert window.results_table.rowCount() == 1
    assert window.output_view.toPlainText() == "PREVIOUS OUTPUT"


def test_one_brand_across_platforms_is_not_prompted(qapp, no_worker_thread):
    window = _build_window_with_previous_run(["core-1", "core-2"], vendors=MIXED)
    window._set_all_checked(True)
    window._ask_mixed_vendor_choice = MagicMock()

    window.run_btn.click()

    window._ask_mixed_vendor_choice.assert_not_called()
    assert _run_device_names(no_worker_thread) == ["core-1", "core-2"]


def test_retry_is_not_prompted_again(qapp, no_worker_thread):
    window = _mixed_window()
    window._ask_mixed_vendor_choice = MagicMock()

    window._start_run(retry_devices={"core-1", "pe-1"})

    window._ask_mixed_vendor_choice.assert_not_called()
