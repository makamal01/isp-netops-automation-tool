"""Device inventory panel: filtering, visible-only selection, and the
selection summary, driven through the real widgets."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

from app.core.deployment_policy import DeploymentPolicy
from app.gui import main_window as main_window_module
from app.gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


INVENTORY = [
    ("core-1", "10.246.222.1", "Cisco IOS-XE"),
    ("core-2", "10.246.222.2", "Cisco IOS-XR"),
    ("pe-1", "10.246.111.1", "Nokia SR OS"),
    ("hw-1", "10.246.99.1", "Huawei VRP"),
]


def _device(name, host, vendor):
    device = MagicMock()
    device.name, device.host, device.vendor = name, host, vendor
    return device


def _build_window(qapp, inventory=INVENTORY):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.deployment_policy = DeploymentPolicy()
    window.username = "tester"
    window.results_by_device = {}
    window.cancel_event = None
    window._build_central_widget()
    window.device_manager = MagicMock()
    window.device_manager.list_devices.return_value = [_device(*row) for row in inventory]
    window.jump_server_manager = MagicMock()
    window.jump_server_manager.get_config.return_value.enabled = True
    window._refresh_device_list()
    return window


def _visible_names(window):
    devices = window.device_manager.list_devices()
    return [devices[i].name for i in range(window.device_list.count()) if not window.device_list.item(i).isHidden()]


def test_all_devices_are_visible_by_default(qapp):
    window = _build_window(qapp)

    assert window.vendor_filter_combo.currentText() == "All vendors"
    assert _visible_names(window) == ["core-1", "core-2", "pe-1", "hw-1"]


def test_vendor_family_filter_hides_other_vendors(qapp):
    window = _build_window(qapp)

    window.vendor_filter_combo.setCurrentText("Cisco (all)")

    assert _visible_names(window) == ["core-1", "core-2"]


def test_search_filters_by_name_or_ip(qapp):
    window = _build_window(qapp)

    window.device_search_edit.setText("10.246.111")

    assert _visible_names(window) == ["pe-1"]


def test_filter_is_reapplied_after_the_device_list_is_rebuilt(qapp):
    window = _build_window(qapp)
    window.vendor_filter_combo.setCurrentText("Nokia SR OS")

    window._refresh_device_list()

    assert _visible_names(window) == ["pe-1"]


def _checked_names(window):
    devices = window.device_manager.list_devices()
    return [devices[i].name for i in range(window.device_list.count())
            if window.device_list.item(i).checkState() == Qt.Checked]


def test_select_all_only_checks_visible_devices(qapp):
    window = _build_window(qapp)
    window.vendor_filter_combo.setCurrentText("Cisco (all)")

    window._set_all_checked(True)

    assert _checked_names(window) == ["core-1", "core-2"]


def test_select_none_leaves_hidden_devices_checked(qapp):
    window = _build_window(qapp)
    window._set_all_checked(True)
    window.vendor_filter_combo.setCurrentText("Cisco (all)")

    window._set_all_checked(False)

    assert _checked_names(window) == ["pe-1", "hw-1"]


def test_hiding_the_current_device_clears_it_so_edit_cannot_target_it(qapp):
    window = _build_window(qapp)
    window.device_list.setCurrentRow(2)  # pe-1 (Nokia)

    window.vendor_filter_combo.setCurrentText("Cisco (all)")

    assert window._selected_device_index() is None


def test_selection_summary_updates_as_devices_are_checked_and_filtered(qapp):
    window = _build_window(qapp)
    assert window.selection_summary_label.text() == "Selected: 0"

    window.device_list.item(0).setCheckState(Qt.Checked)  # core-1, Cisco IOS-XE
    window.device_list.item(2).setCheckState(Qt.Checked)  # pe-1, Nokia SR OS
    window.vendor_filter_combo.setCurrentText("Cisco (all)")

    assert window.selection_summary_label.text() == (
        "Selected: 2, Cisco IOS-XE 1 · Nokia SR OS 1 (1 hidden by filter)"
    )


def _set_inventory(window, rows):
    window.device_manager.list_devices.return_value = [_device(*row) for row in rows]


def test_adding_a_device_keeps_existing_checks(qapp):
    window = _build_window(qapp)
    window.device_list.item(0).setCheckState(Qt.Checked)  # core-1
    window.device_list.item(2).setCheckState(Qt.Checked)  # pe-1

    _set_inventory(window, INVENTORY + [("new-1", "10.246.1.1", "Cisco IOS-XE")])
    window._refresh_device_list()

    assert _checked_names(window) == ["core-1", "pe-1"]


def test_removing_a_device_keeps_checks_on_the_remaining_devices(qapp):
    window = _build_window(qapp)
    window.device_list.item(2).setCheckState(Qt.Checked)  # pe-1

    _set_inventory(window, [row for row in INVENTORY if row[0] != "core-2"])
    window._refresh_device_list()

    assert _checked_names(window) == ["pe-1"]


def test_renaming_a_checked_device_keeps_it_checked(qapp):
    window = _build_window(qapp)
    window.device_list.item(2).setCheckState(Qt.Checked)  # pe-1

    _set_inventory(window, [row if row[0] != "pe-1" else ("pe-1-new", row[1], row[2]) for row in INVENTORY])
    window._refresh_device_list(renamed={"pe-1": "pe-1-new"})

    assert _checked_names(window) == ["pe-1-new"]


def test_selection_summary_reflects_checks_kept_after_rebuild(qapp):
    window = _build_window(qapp)
    window.device_list.item(0).setCheckState(Qt.Checked)

    _set_inventory(window, INVENTORY + [("new-1", "10.246.1.1", "Cisco IOS-XE")])
    window._refresh_device_list()

    assert window.selection_summary_label.text() == "Selected: 1, Cisco IOS-XE 1"


def test_edit_rename_through_the_dialog_keeps_the_check(qapp):
    """update_device mutates the same Device object the handler holds, so
    the old name must be captured before the update."""
    window = _build_window(qapp)
    devices = window.device_manager.list_devices()
    window.device_manager.list_devices.side_effect = lambda: list(devices)
    window.device_manager.update_device.side_effect = (
        lambda index, **fields: setattr(devices[index], "name", fields["name"])
    )
    window.device_list.item(2).setCheckState(Qt.Checked)  # pe-1
    window.device_list.setCurrentRow(2)
    dialog = MagicMock()
    dialog.exec.return_value = main_window_module.QDialog.Accepted
    dialog.result_data = {
        "name": "pe-1-renamed", "host": "10.246.111.1", "vendor": "Nokia SR OS",
        "username": "admin", "port": 22, "password": "", "secret": "",
    }

    with patch.object(main_window_module, "DeviceDialog", return_value=dialog),          patch.object(main_window_module, "audit_log", MagicMock()):
        window._edit_selected_device()

    assert _checked_names(window) == ["pe-1-renamed"]


def test_edit_rejected_by_inventory_shows_a_warning_and_changes_nothing(qapp):
    window = _build_window(qapp)
    window.device_manager.update_device.side_effect = ValueError("Device name 'core-1' already exists.")
    window.device_list.item(2).setCheckState(Qt.Checked)  # pe-1
    window.device_list.setCurrentRow(2)
    dialog = MagicMock()
    dialog.exec.return_value = main_window_module.QDialog.Accepted
    dialog.result_data = {
        "name": "core-1", "host": "10.246.111.1", "vendor": "Nokia SR OS",
        "username": "admin", "port": 22, "password": "", "secret": "",
    }
    audit = MagicMock()

    with patch.object(main_window_module, "DeviceDialog", return_value=dialog), \
         patch.object(main_window_module, "audit_log", audit), \
         patch.object(main_window_module.QMessageBox, "warning") as warning:
        window._edit_selected_device()

    warning.assert_called_once()
    assert "already exists" in warning.call_args.args[2]
    audit.log_event.assert_not_called()
    assert _checked_names(window) == ["pe-1"]
