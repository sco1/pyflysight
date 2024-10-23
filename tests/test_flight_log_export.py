import json
from dataclasses import asdict, fields
from pathlib import Path

import pytest
from polars.testing import assert_frame_equal

from pyflysight.exceptions import MultipleChildLogsError
from pyflysight.flysight_proc import (
    FlysightV2,
    FlysightV2FlightLog,
    NoProcessedFlightLogError,
    SensorInfo,
    parse_v2_log_directory,
)
from tests import SAMPLE_DATA_DIR

SAMPLE_LOG = SAMPLE_DATA_DIR / "24-04-20/04-20-00"

SAMPLE_DEVICE_INFO = FlysightV2(
    firmware_version="a",
    device_id="b",
    session_id="c",
    sensor_info={"SENSOR": SensorInfo(columns=["a"], units=["b"], id_="SENSOR")},
)


def test_flysight_v2_from_json_missing_field_raises() -> None:
    in_json = {"some_random_field": 1}
    with pytest.raises(ValueError, match="Missing required"):
        FlysightV2.from_json(in_json)


def test_flysightv2_roundtrip() -> None:
    device_json = json.loads(json.dumps(asdict(SAMPLE_DEVICE_INFO)))
    device_info = FlysightV2.from_json(device_json)

    check_fields = [field.name for field in fields(FlysightV2)]
    for field in check_fields:
        assert getattr(device_info, field) == getattr(SAMPLE_DEVICE_INFO, field)


def test_flight_log_from_csv_no_device_info_raises(tmp_path: Path) -> None:
    with pytest.raises(NoProcessedFlightLogError, match="device info"):
        FlysightV2FlightLog.from_csv(tmp_path)


def test_flight_log_from_csv_multiple_children_raises(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a/device_info.json").touch()
    (tmp_path / "b").mkdir()
    (tmp_path / "b/device_info.json").touch()
    with pytest.raises(MultipleChildLogsError):
        FlysightV2FlightLog.from_csv(tmp_path)


def test_flight_log_no_track_data_raises(tmp_path: Path) -> None:
    with (tmp_path / "device_info.json").open("w") as f:
        json.dump(asdict(SAMPLE_DEVICE_INFO), f)

    data_file = tmp_path / "IMU.CSV"
    data_file.write_text("a,b\n1,2")
    with pytest.raises(ValueError, match="Track data"):
        FlysightV2FlightLog.from_csv(tmp_path)


def test_flight_log_no_sensor_data_raises(tmp_path: Path) -> None:
    with (tmp_path / "device_info.json").open("w") as f:
        json.dump(asdict(SAMPLE_DEVICE_INFO), f)

    data_file = tmp_path / "TRACK.CSV"
    data_file.write_text("time,b\n2024-04-24T14:46:50.200000,1")
    with pytest.raises(ValueError, match="sensor data"):
        FlysightV2FlightLog.from_csv(tmp_path)


def test_flight_log_roundtrip(tmp_path: Path) -> None:
    truth_flight_log = parse_v2_log_directory(SAMPLE_LOG)
    truth_flight_log.to_csv(tmp_path)

    flight_log = FlysightV2FlightLog.from_csv(tmp_path)

    assert_frame_equal(flight_log.track_data, truth_flight_log.track_data)

    for sensor, df in flight_log.sensor_data.items():
        assert sensor in truth_flight_log.sensor_data
        assert_frame_equal(df, truth_flight_log.sensor_data[sensor])

    check_fields = [field.name for field in fields(FlysightV2)]
    for field in check_fields:
        val = getattr(flight_log.device_info, field)
        truth_val = getattr(truth_flight_log.device_info, field)
        assert val == truth_val


def test_flight_log_export_normalized_gps(tmp_path: Path) -> None:
    # Round tripping tested already, so pull back into flight log instance for easier checking
    truth_flight_log = parse_v2_log_directory(SAMPLE_LOG, normalize_gps=False)
    truth_flight_log.to_csv(tmp_path, normalize_gps=True)
    flight_log = FlysightV2FlightLog.from_csv(tmp_path)

    assert flight_log.track_data["lat"][0] == pytest.approx(0)
    assert flight_log.track_data["lon"][0] == pytest.approx(0)
