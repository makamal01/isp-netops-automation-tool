import csv

from app.core.device_manager import DeviceManager


def test_write_csv_template_has_supported_columns(tmp_path):
    path = tmp_path / "devices_template.csv"

    DeviceManager.write_csv_template(str(path))

    with path.open(newline="", encoding="utf-8-sig") as file:
        assert next(csv.reader(file)) == [
            "name", "host", "vendor", "username", "password", "port", "secret",
        ]