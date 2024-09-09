from pathlib import Path

import pytest
import typer
from pytest_mock import MockerFixture

from pyflysight import FlysightType
from pyflysight.cli import (
    _abort_with_message,
    _check_log_dir,
    _print_connected_drives,
    _trim_pipeline,
    _try_write_config,
    _v2_log_parse2csv_pipeline,
)
from pyflysight.config_utils import FlysightV2Config
from pyflysight.flysight_proc import FlysightV2FlightLog
from pyflysight.flysight_utils import FlysightMetadata


def test_abort_with_message(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(typer.Abort):
        _abort_with_message("Hello")

    captured = capsys.readouterr()
    assert captured.out == "Hello"


DRIVE_METADATA = (
    FlysightMetadata(flysight_type=FlysightType.VERSION_1, serial="ab", firmware="1", n_logs=2),
    FlysightMetadata(flysight_type=FlysightType.VERSION_2, serial="cd", firmware="2", n_logs=1),
)

TRUTH_PRINTED_METADATA = """\
0. A: - FlySight V1, Logs Available: 2
    Serial: ab
    Firmware: 1
1. B: - FlySight V2, Logs Available: 1
    Serial: cd
    Firmware: 2
"""


def test_print_connected_drives(mocker: MockerFixture, capsys: pytest.CaptureFixture) -> None:
    mocker.patch("pyflysight.cli.get_device_metadata", side_effect=DRIVE_METADATA)
    _print_connected_drives((Path("A:"), Path("B:")))

    captured = capsys.readouterr()
    assert captured.out == TRUTH_PRINTED_METADATA


def test_try_write_config(tmp_path: Path) -> None:
    cfg = FlysightV2Config()
    _try_write_config(tmp_path, config=cfg, backup_existing=False)

    assert len(list(tmp_path.glob("CONFIG.TXT"))) == 1


def test_try_write_config_no_permission_raises(tmp_path: Path, mocker: MockerFixture) -> None:
    # I don't understand if permission modes work or not on Windows so will mock instead
    mocker.patch("pyflysight.cli.write_config", side_effect=PermissionError())

    cfg = FlysightV2Config()
    with pytest.raises(typer.Abort):
        _try_write_config(tmp_path, config=cfg, backup_existing=False)


@pytest.mark.parametrize(("hw_type",), ((FlysightType.VERSION_1,), (FlysightType.VERSION_2,)))
def test_check_log_dir_noop(
    hw_type: FlysightType, capsys: pytest.CaptureFixture, mocker: MockerFixture
) -> None:
    mocker.patch("pyflysight.cli.classify_log_dir", return_value=hw_type)
    _check_log_dir(Path())  # Since we're mocking the return, path doesn't matter

    captured = capsys.readouterr()
    assert not captured.out


def test_check_log_dir_fsv2_noop(capsys: pytest.CaptureFixture, mocker: MockerFixture) -> None:
    mocker.patch("pyflysight.cli.classify_log_dir", return_value=FlysightType.VERSION_2)
    _check_log_dir(Path(), v2_only=True)  # Since we're mocking the return, path doesn't matter

    captured = capsys.readouterr()
    assert not captured.out


def test_check_log_dir_no_log_errors(capsys: pytest.CaptureFixture, mocker: MockerFixture) -> None:
    mocker.patch("pyflysight.cli.classify_log_dir", side_effect=ValueError())

    with pytest.raises(typer.Abort):
        _check_log_dir(Path(), v2_only=False)  # Since we're mocking the return, path doesn't matter

    captured = capsys.readouterr()
    assert "No log files" in captured.out


def test_check_log_dir_fsv1_errors(capsys: pytest.CaptureFixture, mocker: MockerFixture) -> None:
    mocker.patch("pyflysight.cli.classify_log_dir", return_value=FlysightType.VERSION_1)

    with pytest.raises(typer.Abort):
        _check_log_dir(Path(), v2_only=True)  # Since we're mocking the return, path doesn't matter

    captured = capsys.readouterr()
    assert "FlySight V1 hardware" in captured.out


def test_trim_pipeline(mocker: MockerFixture) -> None:
    # Since trimming is tested elsewhere & we don't want to need user interaction, check that the
    # helper is called & that it's going to write a CSV
    patched = mocker.patch("pyflysight.cli.windowtrim_flight_log")
    p = Path()
    _trim_pipeline(p, normalize_gps=False)

    patched.assert_called_once_with(p, write_csv=True, normalize_gps=False)


def test_parse2csv_pipeline(dummy_flysight_v2: FlysightV2FlightLog, mocker: MockerFixture) -> None:
    patched_csv_dump = mocker.patch.object(FlysightV2FlightLog, "to_csv")
    patched_parse = mocker.patch(
        "pyflysight.cli.parse_v2_log_directory", return_value=dummy_flysight_v2
    )

    p = Path()
    _v2_log_parse2csv_pipeline(p, normalize_gps=False)

    patched_parse.assert_called_once()
    patched_csv_dump.assert_called_once_with(p)
