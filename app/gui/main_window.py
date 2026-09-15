"""Main application window: device inventory + bulk command execution."""
from datetime import datetime
from pathlib import Path
from threading import Event

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QHBoxLayout, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QTextEdit, QLabel, QCheckBox, QFileDialog, QMessageBox, QInputDialog,
    QLineEdit, QDialog, QProgressBar, QSpinBox
)
from PySide6.QtCore import Qt, QThread, QObject, Signal

from app.core.device_manager import DeviceManager
from app.core.command_runner import run_bulk, DeviceResult, JumpServerError
from app.core.command_safety import filter_safe_commands
from app.core.report import build_text_report, format_device_output
from app.core.jump_server import JumpServerManager
from app.core.deployment_policy import get_deployment_policy
from app.gui.device_dialog import DeviceDialog
from app.gui.jump_server_dialog import JumpServerDialog
from app.gui.validation_dialog import ValidationDialog
from app.gui.host_key_dialog import HostKeyDialog
from app.auth.auth_manager import AuthManager
from app.auth import mfa_manager
from app.gui.mfa_window import MfaEnrollDialog
from app.utils import audit_log
from app.config import REPORTS_DIR, DEFAULT_MAX_WORKERS, DEFAULT_SSH_TIMEOUT


class BulkRunner(QObject):
    """Runs a batch of commands on a thread-pool of devices without blocking
    the Qt event loop. Lives on its own QThread; result_ready/finished are
    Qt signals so cross-thread delivery to the GUI is handled safely."""
    result_ready = Signal(object)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, devices, commands, max_workers, timeout, jump_config=None, cancel_event=None):
        super().__init__()
        self.devices = devices
        self.commands = commands
        self.max_workers = max_workers
        self.timeout = timeout
        self.jump_config = jump_config
        self.cancel_event = cancel_event

    def run(self):
        try:
            results = run_bulk(
                self.devices, self.commands,
                max_workers=self.max_workers, timeout=self.timeout,
                on_result=self.result_ready.emit, jump_config=self.jump_config,
                cancel_event=self.cancel_event,
            )
        except JumpServerError as exc:
            self.error.emit(str(exc))
            return
        self.finished.emit(results)


class MainWindow(QMainWindow):
    def __init__(self, auth_manager: AuthManager, username: str):
        super().__init__()
        self.auth = auth_manager
        self.username = username
        self.device_manager = DeviceManager()
        self.jump_server_manager = JumpServerManager()
        self.deployment_policy = get_deployment_policy()
        self.results_by_device = {}
        self.last_run_commands = []
        self.last_run_safe_mode = self.deployment_policy.safe_mode_default
        self.thread = None
        self.worker = None
        self.cancel_event = None
        self.last_run_devices = []
        self.run_total = 0
        self.run_completed = 0
        self.run_success = 0

        self.setWindowTitle(f"ISP NetOps Tool - logged in as {username}")
        self.resize(1100, 700)

        self._build_menu()
        self._build_central_widget()
        self._refresh_device_list()

    # ---------- UI construction ----------

    def _build_menu(self):
        menu = self.menuBar()
        device_menu = menu.addMenu("Devices")
        device_menu.addAction("Add Device").triggered.connect(self._add_device)
        device_menu.addAction("Edit Selected Device").triggered.connect(self._edit_selected_device)
        device_menu.addAction("Remove Selected Device").triggered.connect(self._remove_selected_device)
        device_menu.addSeparator()
        device_menu.addAction("Import Devices from CSV...").triggered.connect(self._import_devices_csv)
        device_menu.addAction("Export device CSV template...").triggered.connect(self._export_device_template)

        jump_menu = menu.addMenu("JumpServer")
        jump_menu.addAction("Configure JumpServer...").triggered.connect(self._configure_jump_server)

        host_key_menu = menu.addMenu("Host Keys")
        host_key_menu.addAction("Trust SSH Host Key...").triggered.connect(self._open_host_key_dialog)

        validation_menu = menu.addMenu("Validation")
        validation_menu.addAction("MPLS Path Validation...").triggered.connect(self._open_validation_dialog)

        account_menu = menu.addMenu("Account")
        account_menu.addAction("Change Password").triggered.connect(self._change_password)
        account_menu.addAction("Enable MFA").triggered.connect(self._enable_mfa)

    def _build_central_widget(self):
        splitter = QSplitter()

        # Left: device inventory
        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Devices (check to include in run):"))
        self.device_list = QListWidget()
        left_layout.addWidget(self.device_list)

        device_btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_device)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_selected_device)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_selected_device)
        for b in (add_btn, edit_btn, remove_btn):
            device_btns.addWidget(b)
        left_layout.addLayout(device_btns)

        sel_btns = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        sel_btns.addWidget(select_all_btn)
        sel_btns.addWidget(select_none_btn)
        left_layout.addLayout(sel_btns)
        left.setLayout(left_layout)

        # Right: commands + results
        right = QWidget()
        right_layout = QVBoxLayout()

        right_layout.addWidget(QLabel("Commands (one per line, e.g. 'show version'):"))
        self.command_edit = QPlainTextEdit()
        self.command_edit.setPlaceholderText("show version\nshow ip interface brief")
        self.command_edit.setFixedHeight(100)
        right_layout.addWidget(self.command_edit)

        controls = QHBoxLayout()
        self.safe_mode_checkbox = QCheckBox("Safe mode (block config/disruptive commands)")
        self.safe_mode_checkbox.setChecked(self.deployment_policy.safe_mode_default)
        self.safe_mode_checkbox.setEnabled(not self.deployment_policy.allow_unsafe_commands)
        if not self.deployment_policy.allow_unsafe_commands:
            self.safe_mode_checkbox.setToolTip(
                "This deployment is configured for managed-laptop, jumpserver-only use with read-only safety rules."
            )
        controls.addWidget(self.safe_mode_checkbox)

        controls.addWidget(QLabel("Max concurrent:"))
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 200)
        self.max_workers_spin.setValue(DEFAULT_MAX_WORKERS)
        self.max_workers_spin.setToolTip("How many devices to connect to at once.")
        controls.addWidget(self.max_workers_spin)

        controls.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 600)
        self.timeout_spin.setValue(DEFAULT_SSH_TIMEOUT)
        self.timeout_spin.setToolTip("Per-command SSH read timeout, in seconds.")
        controls.addWidget(self.timeout_spin)

        self.run_btn = QPushButton("Run on selected devices")
        self.run_btn.clicked.connect(self._on_run_clicked)
        controls.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.cancel_btn.setEnabled(False)
        controls.addWidget(self.cancel_btn)

        self.retry_btn = QPushButton("Retry failed")
        self.retry_btn.clicked.connect(self._on_retry_failed_clicked)
        self.retry_btn.setEnabled(False)
        controls.addWidget(self.retry_btn)

        self.export_btn = QPushButton("Export results...")
        self.export_btn.clicked.connect(self._export_results)
        self.export_btn.setEnabled(False)
        controls.addWidget(self.export_btn)
        right_layout.addLayout(controls)

        self.status_label = QLabel("Idle.")
        right_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Device", "Status", "Duration (s)"])
        self.results_table.itemSelectionChanged.connect(self._on_result_row_selected)
        right_layout.addWidget(self.results_table)

        right_layout.addWidget(QLabel("Output:"))
        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        right_layout.addWidget(self.output_view)

        right.setLayout(right_layout)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

    # ---------- Device management ----------

    def _refresh_device_list(self):
        self.device_list.clear()
        for device in self.device_manager.list_devices():
            item = QListWidgetItem(f"{device.name} ({device.host}) - {device.vendor}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.device_list.addItem(item)

    def _set_all_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.device_list.count()):
            self.device_list.item(i).setCheckState(state)

    def _add_device(self):
        dialog = DeviceDialog()
        if dialog.exec() == QDialog.Accepted and dialog.result_data:
            data = dialog.result_data
            try:
                self.device_manager.add_device(
                    name=data["name"], host=data["host"], vendor=data["vendor"],
                    username=data["username"], password=data["password"] or "",
                    port=data["port"], secret=data["secret"] or "",
                )
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid device", str(exc))
                return
            audit_log.log_event("device_added", username=self.username, detail=data["name"])
            self._refresh_device_list()

    def _import_devices_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import devices from CSV", filter="CSV files (*.csv)")
        if not path:
            return
        try:
            added, errors = self.device_manager.import_from_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        audit_log.log_event("devices_imported", username=self.username, detail=f"{added} from {path}")
        self._refresh_device_list()
        summary = f"Imported {added} device(s)."
        if errors:
            summary += "\n\nIssues:\n" + "\n".join(errors)
        QMessageBox.information(self, "Import complete", summary)

    def _export_device_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save device CSV template", "devices_template.csv", "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            self.device_manager.write_csv_template(path)
        except OSError as exc:
            QMessageBox.critical(self, "Template export failed", str(exc))
            return
        QMessageBox.information(self, "Template exported", f"Device template saved to:\n{path}")

    def _configure_jump_server(self):
        dialog = JumpServerDialog(self.jump_server_manager)
        if dialog.exec() == QDialog.Accepted:
            audit_log.log_event(
                "jump_server_configured", username=self.username,
                detail=f"enabled={self.jump_server_manager.get_config().enabled}",
            )

    def _open_validation_dialog(self):
        dialog = ValidationDialog(self)
        dialog.exec()

    def _open_host_key_dialog(self):
        dialog = HostKeyDialog(self.jump_server_manager, username=self.username, parent=self)
        dialog.exec()

    def _selected_device_index(self):
        row = self.device_list.currentRow()
        return row if row >= 0 else None

    def _edit_selected_device(self):
        idx = self._selected_device_index()
        if idx is None:
            QMessageBox.information(self, "No selection", "Select a device first.")
            return
        device = self.device_manager.list_devices()[idx]
        dialog = DeviceDialog(device)
        if dialog.exec() == QDialog.Accepted and dialog.result_data:
            data = dialog.result_data
            update_kwargs = {
                "name": data["name"], "host": data["host"], "vendor": data["vendor"],
                "username": data["username"], "port": data["port"],
            }
            if data["password"]:
                update_kwargs["password"] = data["password"]
            if data["secret"]:
                update_kwargs["secret"] = data["secret"]
            self.device_manager.update_device(idx, **update_kwargs)
            audit_log.log_event("device_edited", username=self.username, detail=data["name"])
            self._refresh_device_list()

    def _remove_selected_device(self):
        idx = self._selected_device_index()
        if idx is None:
            QMessageBox.information(self, "No selection", "Select a device first.")
            return
        confirm = QMessageBox.question(self, "Remove device", "Remove the selected device?")
        if confirm == QMessageBox.Yes:
            device_name = self.device_manager.list_devices()[idx].name
            self.device_manager.remove_device(idx)
            audit_log.log_event("device_removed", username=self.username, detail=device_name)
            self._refresh_device_list()

    # ---------- Command execution ----------

    def _clear_rows_for_devices(self, device_names):
        """Remove only the named devices' rows/results, so a retry-scoped run
        doesn't discard evidence already collected for other devices."""
        for row in reversed(range(self.results_table.rowCount())):
            name = self.results_table.item(row, 0).text()
            if name in device_names:
                self.results_table.removeRow(row)
                self.results_by_device.pop(name, None)

    def _on_run_clicked(self, retry_devices=None):
        """Validate scope, reset run state, and start the worker-thread execution.

        `retry_devices`, when set, scopes the reset to just those device names
        (see _on_retry_failed_clicked) so devices that already succeeded keep
        their results in the table and in any subsequent export.
        """
        checked_devices = [
            self.device_manager.list_devices()[i]
            for i in range(self.device_list.count())
            if self.device_list.item(i).checkState() == Qt.Checked
        ]
        if not checked_devices:
            QMessageBox.warning(self, "No devices selected", "Check at least one device to run against.")
            return

        raw_commands = [c for c in self.command_edit.toPlainText().splitlines() if c.strip()]
        if not raw_commands:
            QMessageBox.warning(self, "No commands", "Enter at least one command.")
            return

        if not self.jump_server_manager.get_config().enabled:
            QMessageBox.warning(
                self,
                "JumpServer required",
                "This deployment is configured for managed-laptop access via a jumpserver only. "
                "Configure a jumpserver before running commands.",
            )
            return

        if not self.deployment_policy.allow_unsafe_commands and not self.safe_mode_checkbox.isChecked():
            self.safe_mode_checkbox.setChecked(True)
            QMessageBox.warning(
                self,
                "Safe mode enforced",
                "This organization deployment requires safe mode for all runs. Unsafe commands require an explicit approval workflow.",
            )

        if self.safe_mode_checkbox.isChecked():
            commands, rejected = filter_safe_commands(raw_commands)
            if rejected:
                QMessageBox.warning(
                    self, "Blocked commands",
                    "These commands look like config/disruptive commands and were "
                    "blocked by safe mode:\n\n" + "\n".join(rejected),
                )
            if not commands:
                return
        else:
            commands = raw_commands

        if retry_devices is None:
            self.results_table.setRowCount(0)
            self.results_by_device.clear()
            self.output_view.clear()
        else:
            self._clear_rows_for_devices(retry_devices)
        self.export_btn.setEnabled(False)
        self.retry_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.run_total = len(checked_devices)
        self.run_completed = 0
        self.run_success = 0
        self.progress_bar.setMaximum(self.run_total)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"Running {len(commands)} command(s) on {len(checked_devices)} device(s)...")

        self.last_run_commands = commands
        self.last_run_safe_mode = self.safe_mode_checkbox.isChecked()
        self.last_run_devices = checked_devices
        audit_log.log_event(
            "bulk_run_started", username=self.username,
            detail=f"{len(checked_devices)} device(s), commands={commands}",
        )

        self.thread = QThread()
        jump_config = self.jump_server_manager.get_config()
        self.cancel_event = Event()
        self.worker = BulkRunner(
            checked_devices, commands,
            max_workers=self.max_workers_spin.value(), timeout=self.timeout_spin.value(),
            jump_config=jump_config, cancel_event=self.cancel_event,
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.result_ready.connect(self._on_device_result)
        self.worker.finished.connect(self._on_run_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self._on_run_error)
        self.worker.error.connect(self.thread.quit)
        self.thread.start()

    def _on_cancel_clicked(self):
        """Request cooperative cancellation; active network calls are not force-killed."""
        if self.cancel_event:
            self.cancel_event.set()
            self.cancel_btn.setEnabled(False)
            self.status_label.setText("Cancelling queued devices...")

    def _on_retry_failed_clicked(self):
        """Rerun the last command set only for devices whose prior result failed."""
        failed_names = {
            name for name, result in self.results_by_device.items() if not result.success
        }
        if not failed_names:
            return
        for index, device in enumerate(self.device_manager.list_devices()):
            self.device_list.item(index).setCheckState(
                Qt.Checked if device.name in failed_names else Qt.Unchecked
            )
        self._on_run_clicked(retry_devices=failed_names)

    def _on_device_result(self, result: DeviceResult):
        self.results_by_device[result.device_name] = result
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(result.device_name))
        status = "OK" if result.success else f"FAILED: {result.error}"
        self.results_table.setItem(row, 1, QTableWidgetItem(status))
        self.results_table.setItem(row, 2, QTableWidgetItem(f"{result.duration_seconds:.2f}"))
        if self.results_table.currentRow() < 0:
            self.results_table.setCurrentCell(row, 0)
            self._on_result_row_selected()

        self.run_completed += 1
        if result.success:
            self.run_success += 1
        self.progress_bar.setValue(self.run_completed)
        failed_so_far = self.run_completed - self.run_success
        self.status_label.setText(
            f"Running... {self.run_completed}/{self.run_total} device(s) complete "
            f"({self.run_success} succeeded, {failed_so_far} failed)"
        )

    def _on_run_finished(self, results):
        """Restore controls, summarize completion, audit the run, and save metadata."""
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.export_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        success_count = sum(1 for r in results if r.success)
        cancelled = sum(1 for r in results if r.error == "Cancelled by operator")
        self.retry_btn.setEnabled(any(not r.success for r in results))
        if cancelled:
            self.status_label.setText(
                f"Cancelled. {success_count}/{len(results)} devices succeeded; {cancelled} cancelled."
            )
        else:
            self.status_label.setText(f"Done. {success_count}/{len(results)} devices succeeded.")
        audit_log.log_event(
            "bulk_run_finished", username=self.username,
            detail=f"{success_count}/{len(results)} succeeded",
        )
        self._auto_save_report()

    def _on_run_error(self, message: str):
        """Handle a worker-level JumpServer failure separately from device results."""
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Run failed.")
        audit_log.log_event("bulk_run_failed", username=self.username, detail=message)
        QMessageBox.critical(self, "JumpServer error", message)

    def _auto_save_report(self):
        """Persist every run's readable text report to the app's reports
        folder automatically, independent of the user clicking Export."""
        report_text = build_text_report(
            self.username, self.last_run_commands, self.results_by_device,
            self.last_run_safe_mode, include_output=False,
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"run_{timestamp}.txt"
        report_path.write_text(report_text, encoding="utf-8")

    def _on_result_row_selected(self):
        row = self.results_table.currentRow()
        if row < 0:
            return
        device_name = self.results_table.item(row, 0).text()
        result = self.results_by_device.get(device_name)
        if result:
            self.output_view.setPlainText(result.output if result.success else result.error)

    def _export_results(self):
        folder = QFileDialog.getExistingDirectory(self, "Select export folder")
        if not folder:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(folder) / f"isp_netops_export_{timestamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        report_text = build_text_report(
            self.username, self.last_run_commands, self.results_by_device, self.last_run_safe_mode,
        )
        (out_dir / "report.txt").write_text(report_text, encoding="utf-8")

        for name, result in self.results_by_device.items():
            safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")) or "device"
            parsed_content = format_device_output(result, self.last_run_commands)
            (out_dir / f"{safe_name}_parsed.txt").write_text(parsed_content, encoding="utf-8")
            if result.success:
                raw_content = format_device_output(result, self.last_run_commands, raw=True)
                (out_dir / f"{safe_name}_raw.txt").write_text(raw_content, encoding="utf-8")
        audit_log.log_event("results_exported", username=self.username, detail=str(out_dir))
        QMessageBox.information(self, "Exported", f"Results exported to:\n{out_dir}")

    # ---------- Account ----------

    def _change_password(self):
        current, ok = QInputDialog.getText(self, "Change Password", "Current password:", QLineEdit.Password)
        if not ok:
            return
        if not self.auth.verify_password(self.username, current):
            QMessageBox.critical(self, "Error", "Current password is incorrect.")
            return
        new_pw, ok = QInputDialog.getText(self, "Change Password", "New password:", QLineEdit.Password)
        if not ok or len(new_pw) < 8:
            QMessageBox.warning(self, "Weak password", "Use at least 8 characters.")
            return
        self.auth.set_password(self.username, new_pw)
        QMessageBox.information(self, "Success", "Password changed.")

    def _enable_mfa(self):
        user = self.auth.get_user(self.username)
        if user.mfa_enabled:
            QMessageBox.information(self, "MFA", "MFA is already enabled for this account.")
            return
        secret = mfa_manager.generate_secret()
        dialog = MfaEnrollDialog(self.username, secret)
        if dialog.exec() == QDialog.Accepted:
            self.auth.enable_mfa(self.username, secret)
            QMessageBox.information(self, "MFA enabled", "MFA has been enabled for your account.")
