from pathlib import Path

import pytest

from pyflysight import FlysightType
from pyflysight.config_utils import FlysightV2Config
from pyflysight.flysight_utils import classify_hardware_type, write_config


def test_hardware_type_no_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Could not locate"):
        classify_hardware_type(tmp_path)


def test_hardware_type_no_data_raises(tmp_path: Path) -> None:
    (tmp_path / "FLYSIGHT.TXT").touch()
    with pytest.raises(ValueError, match="Could not identify"):
        classify_hardware_type(tmp_path)


SAMPLE_V1_STATE = """\
FlySight - http://flysight.ca/
Processor serial number: 1234567890
Firmware version: v20170405
"""

SAMPLE_V2_STATE = """\
; FlySight - http://flysight.ca

; Firmware version

FUS_Ver:      1.2.0
Stack_Ver:    1.17.2
Firmware_Ver: v2024.05.25.pairing_request

<...>
"""

HARDWARE_CLASSIFICATION_CASES = (
    (SAMPLE_V1_STATE, FlysightType.VERSION_1),
    (SAMPLE_V2_STATE, FlysightType.VERSION_2),
)


@pytest.mark.parametrize(("device_state", "truth_hardware_type"), HARDWARE_CLASSIFICATION_CASES)
def test_hardware_type_classification(
    tmp_path: Path, device_state: str, truth_hardware_type: FlysightType
) -> None:
    (tmp_path / "FLYSIGHT.TXT").write_text(device_state)
    assert classify_hardware_type(tmp_path) == truth_hardware_type


def test_write_config_no_drive_raises(tmp_path: Path) -> None:
    fake_dir = tmp_path / "invisible/"
    with pytest.raises(ValueError, match="Device root"):
        write_config(device_root=fake_dir, config=FlysightV2Config())


def test_write_config_not_dir_raises(tmp_path: Path) -> None:
    fake_dir = tmp_path / "not_a_dir.txt"
    with pytest.raises(ValueError, match="Device root"):
        write_config(device_root=fake_dir, config=FlysightV2Config())


def test_write_config_backup_existing(tmp_path: Path) -> None:
    config_filepath = tmp_path / "CONFIG.TXT"
    config_filepath.write_text("hello")

    # Testing of actual config writing tested elsewhere
    write_config(device_root=tmp_path, config=FlysightV2Config(), backup_existing=True)

    backup_config_filepath = tmp_path / "CONFIG_OLD.TXT"
    assert backup_config_filepath.exists()
    assert backup_config_filepath.read_text() == "hello"


def test_write_config_overwrite_existing(tmp_path: Path) -> None:
    config_filepath = tmp_path / "CONFIG.TXT"
    config_filepath.write_text("hello")

    # Testing of actual config writing tested elsewhere
    write_config(device_root=tmp_path, config=FlysightV2Config(), backup_existing=False)

    backup_config_filepath = tmp_path / "CONFIG_OLD.TXT"
    assert not backup_config_filepath.exists()
