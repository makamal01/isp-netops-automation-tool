"""Device inventory panel: filtering, visible-only selection, and the
selection summary, driven through the real widgets."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

from app.core.deployment_policy import DeploymentPolicy
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


def test_hiding_the_current_device_clears_it_so_edit_cannot_target_it(qapp):
    window = _build_window(qapp)
    window.device_list.setCurrentRow(2)  # pe-1 (Nokia)

    window.vendor_filter_combo.setCurrentText("Cisco (all)")

    assert window._selected_device_index() is None
