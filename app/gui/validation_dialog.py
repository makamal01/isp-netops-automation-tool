"""Validation dashboard dialog for layered MPLS path checks."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from app.core.validation.engine import ValidationEngine
from app.core.validation.models import ValidationRequest


class ValidationDialog(QDialog):
    """Simple, non-invasive validation dashboard scaffold.

    This is intentionally limited to a safe first UI hook. It uses the staged
    model and does not alter the current bulk command app logic.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MPLS Path Validation")
        self.resize(760, 500)
        self.engine = ValidationEngine()
        self.device_manager = getattr(parent, "device_manager", None)
        self.jump_server_manager = getattr(parent, "jump_server_manager", None)

        self.side_a_edit = QComboBox()
        self.side_b_edit = QComboBox()
        self._populate_devices()

        self.vendor_combo = QComboBox()
        self.vendor_combo.addItems(["Cisco", "Huawei", "Nokia"])
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["IOS-XR", "IOS-XE", "SR OS", "VRP"])
        self.service_combo = QComboBox()
        self.service_combo.addItems(["L3VPN", "L2VPN", "EVPN", "Generic MPLS"])
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["full_chain", "single_stage"])
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["IGP", "MPLS", "LSP", "BGP", "MP-BGP/VPN"])

        form = QFormLayout()
        form.addRow("Side A device", self.side_a_edit)
        form.addRow("Side B device", self.side_b_edit)
        form.addRow("Vendor", self.vendor_combo)
        form.addRow("Platform", self.platform_combo)
        form.addRow("Service Type", self.service_combo)
        form.addRow("Mode", self.mode_combo)
        form.addRow("Protocol focus", self.protocol_combo)

        self.summary_label = QLabel("Validation summary: waiting for input")
        self.summary_label.setStyleSheet("font-weight: bold; color: #1f3b5b;")

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Validation output will appear here.")
        self.results.setStyleSheet(
            "background-color: #f7f9fc; color: #1a1a1a; border: 1px solid #d9e1ec; border-radius: 6px;"
        )

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._run_validation)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.summary_label)
        layout.addWidget(QLabel("Result:"))
        layout.addWidget(self.results)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _populate_devices(self):
        if self.device_manager is None:
            self.side_a_edit.addItem("No devices available")
            self.side_b_edit.addItem("No devices available")
            return

        devices = self.device_manager.list_devices()
        if not devices:
            self.side_a_edit.addItem("No devices available")
            self.side_b_edit.addItem("No devices available")
            return

        for device in devices:
            self.side_a_edit.addItem(device.name)
            self.side_b_edit.addItem(device.name)

        self.side_a_edit.setCurrentIndex(0)
        self.side_b_edit.setCurrentIndex(1 if len(devices) > 1 else 0)

    def _stage_color(self, status: str) -> str:
        status_key = (status or "unknown").lower()
        colors = {
            "passed": "#1d6f42",
            "failed": "#9b2c2c",
            "unknown": "#7b6b2f",
        }
        return colors.get(status_key, "#4b5563")

    def _build_device_blocks(self, stage) -> str:
        """Per-device breakdown so the operator can see which side of the
        path failed, instead of only a merged stage-level verdict."""
        if not stage.device_results:
            return ""

        rows = []
        for device_result in stage.device_results:
            evidence = (
                "<br/>".join(f"&nbsp;&nbsp;• {item}" for item in device_result.evidence)
                if device_result.evidence else "&nbsp;&nbsp;• No evidence captured."
            )
            rows.append(
                "<div style='margin-top: 6px; padding: 6px 10px; border-left: 3px solid "
                f"{self._stage_color(device_result.status)}; background: #ffffff;'>"
                f"<b>{device_result.device_name}</b> ({device_result.host}) - "
                f"<span style='color: {self._stage_color(device_result.status)}; font-weight: bold;'>"
                f"{device_result.status.upper()}</span><br/>{evidence}"
                "</div>"
            )
        return "<div style='margin-top: 8px;'><b>Per-device results:</b>" + "".join(rows) + "</div>"

    def _build_result_html(self, result) -> str:
        status_color = self._stage_color(result.overall_status)
        stage_blocks = []
        for stage in result.stage_results:
            evidence = "<br/>".join(f"• {item}" for item in stage.evidence) if stage.evidence else "• No evidence captured."
            commands = ", ".join(stage.commands) if stage.commands else "None"
            device_blocks = self._build_device_blocks(stage)
            stage_blocks.append(
                "<div style='margin-top: 12px; padding: 10px 12px; border: 1px solid #dfe7f2; border-radius: 6px; background: #fafcff;'>"
                f"<b>{stage.stage}</b> - <span style='color: {self._stage_color(stage.status)}; font-weight: bold;'>{stage.status.upper()}</span> "
                f"[<span style='color: #475569;'>{stage.confidence.upper()}</span>] <br/>"
                f"<b>Evidence:</b><br/>{evidence}<br/>"
                f"<b>Commands:</b> {commands}<br/>"
                f"<b>Next step:</b> {stage.next_step or 'No specific step required.'}"
                f"{device_blocks}"
                "</div>"
            )

        return (
            "<html><body style='font-family: Segoe UI, sans-serif; font-size: 11pt;'>"
            f"<div style='margin-bottom: 10px;'><b>Overall status:</b> "
            f"<span style='color: {status_color}; font-weight: bold;'>{result.overall_status.upper()}</span></div>"
            f"<div><b>Failed stage:</b> {result.failed_stage or 'None'}</div>"
            f"<div><b>Root cause:</b> {result.root_cause}</div>"
            f"<div><b>Recommendation:</b> {result.recommendation}</div>"
            "<h3 style='margin-bottom: 6px; margin-top: 14px;'>Stage results</h3>"
            f"{''.join(stage_blocks)}"
            "</body></html>"
        )

    def _run_validation(self):
        try:
            if self.device_manager is None or not self.device_manager.list_devices():
                QMessageBox.warning(self, "No devices configured", "Add at least two devices to the inventory before running validation.")
                return

            selected_a = self.side_a_edit.currentText()
            selected_b = self.side_b_edit.currentText()
            if selected_a == selected_b:
                QMessageBox.warning(self, "Choose two devices", "Select two distinct devices for the validation path.")
                return

            devices = self.device_manager.list_devices()
            device_map = {device.name: device for device in devices}
            chosen_devices = [device_map[selected_a], device_map[selected_b]]

            request = ValidationRequest(
                side_a=selected_a,
                side_b=selected_b,
                vendor=self.vendor_combo.currentText(),
                platform=self.platform_combo.currentText(),
                service_type=self.service_combo.currentText(),
                mode=self.mode_combo.currentText(),
                protocol_focus=self.protocol_combo.currentText(),
            )
            jump_config = self.jump_server_manager.get_config() if self.jump_server_manager else None
            result = self.engine.validate(request, devices=chosen_devices, jump_config=jump_config)

            self.summary_label.setText(
                f"Validation summary: {result.overall_status.upper()} | "
                f"Failed stage: {result.failed_stage or 'None'} | "
                f"Stages checked: {len(result.stage_results)}"
            )

            if result.overall_status == "passed":
                self.summary_label.setStyleSheet("font-weight: bold; color: #1d6f42;")
            else:
                self.summary_label.setStyleSheet("font-weight: bold; color: #9b2c2c;")

            self.results.setHtml(self._build_result_html(result))
            if result.overall_status == "failed":
                QMessageBox.warning(
                    self,
                    "Validation failed",
                    result.root_cause or "The validation checks did not pass for the selected path.",
                )
            else:
                QMessageBox.information(self, "Validation complete", "The validation engine completed the selected path check.")
        except Exception as exc:  # pragma: no cover - UI-level safety only
            QMessageBox.critical(self, "Validation failed", f"Validation did not complete cleanly: {exc}")
