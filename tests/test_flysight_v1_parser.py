import datetime as dt
from textwrap import dedent

import polars
import pytest
from polars.testing import assert_frame_equal

from pyflysight import FlysightType, flysight_proc
from tests import SAMPLE_DATA_DIR, checks

BATCH_LOG_STEMS = {
    "21-04-20",
    "21-05-20",
}


def test_log_parse() -> None:
    sample_flight_log = SAMPLE_DATA_DIR / "21-04-20.CSV"  # Test log with single data row
    flight_log = flysight_proc.load_flysight(sample_flight_log)

    DERIVED_COLS = ("time", "elapsed_time", "groundspeed")
    for col_name in DERIVED_COLS:
        checks.is_col(flight_log.track_data, col_name)

    truth_dt = dt.datetime.strptime("2021-04-20T12:34:20.00Z", r"%Y-%m-%dT%H:%M:%S.%f%z")
    TRUTH_DERIVED = polars.DataFrame(
        {
            "time": [truth_dt],
            "elapsed_time": [0.0],
            "groundspeed": [1.165],
        }
    )
    assert_frame_equal(flight_log.track_data.select(DERIVED_COLS), TRUTH_DERIVED, rtol=1e-3)


def test_device_info_parse() -> None:
    sample_flight_log = SAMPLE_DATA_DIR / "21-04-20.CSV"  # Test log with single data row
    flight_log = flysight_proc.load_flysight(sample_flight_log)

    assert flight_log.device_info.flysight_type == FlysightType.VERSION_1

    # fmt: off
    truth_sensor_info = flysight_proc.SensorInfo(
        columns=["time", "lat", "lon", "hMSL", "velN", "velE", "velD", "hAcc", "vAcc", "sAcc", "heading", "cAcc", "gpsFix", "numSV"],
        units=["datetime", "deg", "deg", "m", "m/s", "m/s", "m/s", "m", "m", "m/s", "deg", "deg", "", ""],
        id_="GNSS",
    )
    # fmt: on

    assert "GNSS" in flight_log.device_info.sensor_info.keys()
    assert flight_log.device_info.sensor_info["GNSS"] == truth_sensor_info


def test_log_parse_normalize_gps() -> None:
    sample_flight_log = SAMPLE_DATA_DIR / "21-04-20.CSV"  # Test log with single data row
    flight_log = flysight_proc.load_flysight(sample_flight_log, normalize_gps=True)

    # Normalization helper tested elsewhere, just check here that the flag is being acted on
    assert flight_log.track_data["lat"][0] == pytest.approx(0)
    assert flight_log.track_data["lon"][0] == pytest.approx(0)


def test_log_parse_normalize_gps_method() -> None:
    sample_flight_log = SAMPLE_DATA_DIR / "21-04-20.CSV"  # Test log with single data row
    flight_log = flysight_proc.load_flysight(sample_flight_log, normalize_gps=False)
    flight_log.normalize_gps()

    # Normalization helper tested elsewhere, just check here that the flag is being acted on
    assert flight_log.track_data["lat"][0] == pytest.approx(0)
    assert flight_log.track_data["lon"][0] == pytest.approx(0)


def test_batch_log_parse() -> None:
    sample_log_pattern = "21*.CSV"  # Limit to a subset of the sample data
    flight_logs = flysight_proc.batch_load_flysight(SAMPLE_DATA_DIR, pattern=sample_log_pattern)

    # Check top level dir name
    dir_name = SAMPLE_DATA_DIR.name
    assert dir_name in flight_logs

    # Check that the log files are loaded & keyed correctly
    assert set(flight_logs[dir_name]) == BATCH_LOG_STEMS


def test_batch_log_parse_normalize_gps() -> None:
    sample_log_pattern = "21*.CSV"  # Limit to a subset of the sample data
    flight_logs = flysight_proc.batch_load_flysight(
        SAMPLE_DATA_DIR, pattern=sample_log_pattern, normalize_gps=True
    )

    # Normalization helper tested elsewhere, just check here that the flag is being acted on
    for fl in flight_logs[SAMPLE_DATA_DIR.name].values():
        assert fl.track_data["lat"][0] == pytest.approx(0)
        assert fl.track_data["lon"][0] == pytest.approx(0)


SAMPLE_DATA_TO_SPLIT = dedent(
    """\
    a,b,c
    d,e,f
    1,2,3
    """
)


def test_v1_data_split() -> None:
    header, data = flysight_proc._split_sensor_data(
        SAMPLE_DATA_TO_SPLIT.splitlines(), hardware_type=FlysightType.VERSION_1
    )
    assert header == ["a,b,c", "d,e,f"]
    assert data == ["1,2,3"]
