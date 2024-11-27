from pathlib import Path

import pytest

from pyflysight import FlysightType
from pyflysight.config_utils import FlysightV2Config
from pyflysight.flysight_utils import (
    FlysightMetadata,
    NoDeviceStateError,
    UnknownDeviceError,
    classify_hardware_type,
    copy_logs,
    erase_logs,
    get_device_metadata,
    write_config,
)


def test_hardware_type_no_file_raises(tmp_path: Path) -> None:
    with pytest.raises(NoDeviceStateError):
        classify_hardware_type(tmp_path)


def test_hardware_type_no_data_raises(tmp_path: Path) -> None:
    (tmp_path / "FLYSIGHT.TXT").touch()
    with pytest.raises(UnknownDeviceError):
        classify_hardware_type(tmp_path)


SAMPLE_V1_STATE = """\
FlySight - http://flysight.ca/
Processor serial number: 1234567890
Firmware version: v123abc
"""

SAMPLE_V2_STATE = """\
; FlySight - http://flysight.ca

; Firmware version

FUS_Ver:      1.2.0
Stack_Ver:    1.17.2
Firmware_Ver: v123abc

; Device information

Device_ID:    1234567890
Session_ID:   abc123
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


FLYSIGHT_V1_FILE_STRUCTURE = {
    "23-04-21": ("04-20-00.CSV",),
    "24-04-21": ("04-20-00.CSV", "05-20-00.CSV"),
}


def _build_dummy_v1_device(top_dir: Path) -> Path:
    flysight_device = top_dir / "flysight"
    flysight_device.mkdir()
    (flysight_device / "FLYSIGHT.TXT").write_text(SAMPLE_V1_STATE)
    for d, fnames in FLYSIGHT_V1_FILE_STRUCTURE.items():
        log_dir = flysight_device / d
        log_dir.mkdir()
        for f in fnames:
            (log_dir / f).touch()

    return flysight_device


FLYSIGHT_V2_FILE_STRUCTURE = (
    "23-04-20/04-20-00",
    "24-04-20/04-20-00",
)


def _build_dummy_v2_device(top_dir: Path) -> Path:
    flysight_device = top_dir / "flysight"
    flysight_device.mkdir()
    (flysight_device / "FLYSIGHT.TXT").write_text(SAMPLE_V2_STATE)
    for d in FLYSIGHT_V2_FILE_STRUCTURE:
        log_dir = flysight_device / d
        log_dir.mkdir(parents=True)
        for f in ("RAW.UBX", "SENSOR.CSV", "TRACK.CSV"):
            (log_dir / f).touch()

    return flysight_device


def _build_dummy_v2_device_with_temp(top_dir: Path) -> Path:
    flysight_device = _build_dummy_v2_device(top_dir)
    temp_dir = flysight_device / "TEMP"
    temp_dir.mkdir()
    for f in ("RAW.UBX", "SENSOR.CSV", "TRACK.CSV"):
        (temp_dir / f).touch()

    return flysight_device


def test_get_v1_device_metadata(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v1_device(tmp_path)

    truth_metadata = FlysightMetadata(
        flysight_type=FlysightType.VERSION_1,
        serial="1234567890",
        firmware="v123abc",
        n_logs=3,
        n_temp_logs=0,  # V1 hardware should always have 0 temporary logs
    )
    assert get_device_metadata(flysight_device) == truth_metadata
    assert FlysightMetadata.from_drive(flysight_device) == truth_metadata


def test_get_v2_device_metadata_no_temp(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device(tmp_path)
    truth_metadata = FlysightMetadata(
        flysight_type=FlysightType.VERSION_2,
        serial="1234567890",
        firmware="v123abc",
        n_logs=2,
        n_temp_logs=0,
    )
    assert get_device_metadata(flysight_device) == truth_metadata
    assert FlysightMetadata.from_drive(flysight_device) == truth_metadata


def test_get_v2_device_metadata_with_temp(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device_with_temp(tmp_path)
    truth_metadata = FlysightMetadata(
        flysight_type=FlysightType.VERSION_2,
        serial="1234567890",
        firmware="v123abc",
        n_logs=2,
        n_temp_logs=1,
    )
    assert get_device_metadata(flysight_device) == truth_metadata
    assert FlysightMetadata.from_drive(flysight_device) == truth_metadata


def test_copy_v1_logs(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v1_device(tmp_path)

    dest = tmp_path / "copied"
    copy_logs(device_root=flysight_device, dest=dest)

    log_filenames = {f.name for f in flysight_device.rglob("*.CSV")}
    copied_filenames = {f.name for f in dest.rglob("*.CSV")}
    assert copied_filenames == log_filenames


def test_copy_v2_logs(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device(tmp_path)

    dest = tmp_path / "copied"
    copy_logs(device_root=flysight_device, dest=dest)

    log_filenames = {f.name for f in flysight_device.rglob("*.CSV")}
    copied_filenames = {f.name for f in dest.rglob("*.CSV")}
    assert copied_filenames == log_filenames


def sample_filter(log_dir: Path) -> bool:
    if log_dir.parent.name.startswith("23"):
        return False
    else:
        return True


def test_copy_logs_with_filter(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device(tmp_path)

    dest = tmp_path / "copied"
    copy_logs(device_root=flysight_device, dest=dest, filter_func=sample_filter)
    assert len(list(dest.glob("*"))) == 1


def test_copy_logs_remove_after(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device(tmp_path)

    dest = tmp_path / "copied"
    copy_logs(device_root=flysight_device, dest=dest, remove_after=True)

    log_files = tuple(flysight_device.rglob("*.CSV"))
    assert len(log_files) == 0


def test_copy_logs_with_filter_remove_after(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device(tmp_path)

    dest = tmp_path / "copied"
    copy_logs(device_root=flysight_device, dest=dest, filter_func=sample_filter, remove_after=True)

    log_filenames = tuple(flysight_device.rglob("*.CSV"))
    assert len(log_filenames) == 2


def test_remove_logs(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device(tmp_path)

    erase_logs(flysight_device)
    log_files = tuple(flysight_device.rglob("*.CSV"))
    assert len(log_files) == 0


def test_remove_logs_with_filter(tmp_path: Path) -> None:
    flysight_device = _build_dummy_v2_device(tmp_path)

    erase_logs(flysight_device, filter_func=sample_filter)
    log_files = tuple(flysight_device.rglob("*.CSV"))
    assert len(log_files) == 2
