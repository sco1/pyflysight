import datetime as dt
from pathlib import Path
from textwrap import dedent

import polars
import pytest
from polars.testing import assert_frame_equal

from pyflysight.exceptions import HeadingParseError, RawLogParseError
from pyflysight.flysight_proc import (
    FlysightV2,
    SensorInfo,
    _calculate_derived_columns,
    _parse_header,
    _partition_sensor_data,
    _raw_data_to_dataframe,
    _split_sensor_data,
    calculate_sync_delta,
    parse_v2_log_directory,
    parse_v2_sensor_data,
    parse_v2_track_data,
)
from tests import SAMPLE_DATA_DIR

SAMPLE_SPLIT_FILE = dedent(
    """\
    $UNIT,VBAT,s,volt
    $DATA
    $IMU,59970.376,-0.427,1.770,1.953,-0.01464,-0.00732,0.94287,25.64
    """
).splitlines()


def test_v2_data_split() -> None:
    header, data = _split_sensor_data(SAMPLE_SPLIT_FILE)
    assert header == ["$UNIT,VBAT,s,volt"]
    assert data == ["$IMU,59970.376,-0.427,1.770,1.953,-0.01464,-0.00732,0.94287,25.64"]


def test_data_split_no_partition_raises() -> None:
    with pytest.raises(RawLogParseError, match="HELLO"):
        _ = _split_sensor_data(SAMPLE_SPLIT_FILE, partition_keyword="$HELLO")


SAMPLE_HEADER_ONE_SENSOR = dedent(
    """\
    $FLYS,1
    $VAR,FIRMWARE_VER,v2023.09.22
    $VAR,DEVICE_ID,003f0033484e501420353131
    $VAR,SESSION_ID,7e67d0e71a53d9d6486b0114
    $COL,BARO,time,pressure,temperature
    $UNIT,BARO,s,Pa,deg C
    """
).splitlines()

TRUTH_SENSOR_INFO = SensorInfo(
    columns=["time", "pressure", "temperature"],
    units=["s", "Pa", "deg C"],
    id_="BARO",
)


def test_header_parse_one_sensor() -> None:
    flysight = _parse_header(SAMPLE_HEADER_ONE_SENSOR)
    assert flysight.firmware_version == "v2023.09.22"
    assert flysight.device_id == "003f0033484e501420353131"
    assert flysight.session_id == "7e67d0e71a53d9d6486b0114"

    assert "BARO" in flysight.sensor_info
    assert flysight.sensor_info["BARO"] == TRUTH_SENSOR_INFO


SAMPLE_HEADER_NO_FIRMWARE = dedent(
    """\
    $FLYS,1
    $VAR,DEVICE_ID,003f0033484e501420353131
    $VAR,SESSION_ID,7e67d0e71a53d9d6486b0114
    """
).splitlines()


def test_header_missing_firmware_raises() -> None:
    with pytest.raises(HeadingParseError, match="firmware"):
        _parse_header(SAMPLE_HEADER_NO_FIRMWARE)


SAMPLE_HEADER_NO_DEVICE_ID = dedent(
    """\
    $FLYS,1
    $VAR,FIRMWARE_VER,v2023.09.22
    $VAR,SESSION_ID,7e67d0e71a53d9d6486b0114
    """
).splitlines()


def test_header_missing_device_raises() -> None:
    with pytest.raises(HeadingParseError, match="device"):
        _parse_header(SAMPLE_HEADER_NO_DEVICE_ID)


SAMPLE_HEADER_NO_SESSION_ID = dedent(
    """\
    $FLYS,1
    $VAR,FIRMWARE_VER,v2023.09.22
    $VAR,DEVICE_ID,003f0033484e501420353131
    """
).splitlines()


def test_header_missing_session_raises() -> None:
    with pytest.raises(HeadingParseError, match="session"):
        _parse_header(SAMPLE_HEADER_NO_SESSION_ID)


SAMPLE_HEADER_MISMATCHED_SENSOR_INFO = dedent(
    """\
    $FLYS,1
    $VAR,FIRMWARE_VER,v2023.09.22
    $VAR,DEVICE_ID,003f0033484e501420353131
    $VAR,SESSION_ID,7e67d0e71a53d9d6486b0114
    $COL,BARO,time,pressure,temperature
    """
).splitlines()


def test_header_partial_missing_sensor_info_raises() -> None:
    with pytest.raises(HeadingParseError, match="lacks column or unit information"):
        _parse_header(SAMPLE_HEADER_MISMATCHED_SENSOR_INFO)


SAMPLE_HEADER_GNSS_INFO = dedent(
    """\
    $FLYS,1
    $VAR,FIRMWARE_VER,v2023.09.22
    $VAR,DEVICE_ID,003f0033484e501420353131
    $VAR,SESSION_ID,7e67d0e71a53d9d6486b0114
    $COL,GNSS,time,lat,lon,hMSL,velN,velE,velD,hAcc,vAcc,sAcc,numSV
    $UNIT,GNSS,,deg,deg,m,m/s,m/s,m/s,m,m,m/s,
    """
).splitlines()


def test_header_gnss_datetime_unit_fill() -> None:
    flysight = _parse_header(SAMPLE_HEADER_GNSS_INFO)
    assert "datetime" in flysight.sensor_info["GNSS"].units


SAMPLE_SENSOR_DATA_SINGLE_LINES = dedent(
    """\
    $IMU,1,2,3,4
    $BARO,5,6,7,8
    """
).splitlines()


def test_sensor_data_partition() -> None:
    sensor_data, initial_timestamp = _partition_sensor_data(SAMPLE_SENSOR_DATA_SINGLE_LINES)

    assert initial_timestamp == pytest.approx(1)

    assert not (sensor_data.keys() - {"IMU", "BARO"})

    assert len(sensor_data["IMU"]) == 1
    assert sensor_data["IMU"][0] == pytest.approx([1, 2, 3, 4])

    assert len(sensor_data["BARO"]) == 1
    assert sensor_data["BARO"][0] == pytest.approx([5, 6, 7, 8])


SAMPLE_SENSOR_DATA_MULTI_LINES = dedent(
    """\
    $IMU,1,2
    $BARO,3,4
    $IMU,5,6
    """
).splitlines()


def test_sensor_data_partition_multi_line() -> None:
    sensor_data, _ = _partition_sensor_data(SAMPLE_SENSOR_DATA_MULTI_LINES)
    assert not (sensor_data.keys() - {"IMU", "BARO"})

    assert len(sensor_data["IMU"]) == 2
    assert sensor_data["IMU"][0] == pytest.approx([1, 2])
    assert sensor_data["IMU"][1] == pytest.approx([5, 6])

    assert len(sensor_data["BARO"]) == 1
    assert sensor_data["BARO"][0] == pytest.approx([3, 4])


DEVICE_INFO_NO_TIMESTAMP = FlysightV2(
    firmware_version="abc123",
    device_id="abc123",
    session_id="abc123",
    sensor_info={"BARO": TRUTH_SENSOR_INFO},
)

SAMPLE_GROUPED_DATA = {"BARO": [[1.0, 2.0, 3.0]]}


def test_dataframe_conversion_no_timestamp_raises() -> None:
    with pytest.raises(RawLogParseError, match="timestamp"):
        _raw_data_to_dataframe(SAMPLE_GROUPED_DATA, DEVICE_INFO_NO_TIMESTAMP)


DEVICE_INFO_WITH_TIMESTAMP = FlysightV2(
    firmware_version="abc123",
    device_id="abc123",
    session_id="abc123",
    sensor_info={"BARO": TRUTH_SENSOR_INFO},
    first_sensor_timestamp=0.5,
)


def test_dataframe_conversion_mismatch_column_headers_raises() -> None:
    sample_data = {"BARO": [[1.0, 2.0, 3.0, 4.0]]}
    with pytest.raises(HeadingParseError, match="Number of column headers"):
        _raw_data_to_dataframe(sample_data, DEVICE_INFO_WITH_TIMESTAMP)


def test_dataframe_conversion_no_column_headers_raises() -> None:
    sample_data = {"abcd": [[1.0, 2.0, 3.0]]}
    with pytest.raises(HeadingParseError, match="Could not locate"):
        _raw_data_to_dataframe(sample_data, DEVICE_INFO_WITH_TIMESTAMP)


def test_dataframe_elapsed_time_derived() -> None:
    parsed_sensor_data = _raw_data_to_dataframe(SAMPLE_GROUPED_DATA, DEVICE_INFO_WITH_TIMESTAMP)
    df = parsed_sensor_data["BARO"]

    assert "elapsed_time" in df.columns
    assert df.select(polars.col("elapsed_time").first()).item() == pytest.approx(0.5)


def test_dataframe_pressure_altitude_from_baro() -> None:
    parsed_sensor_data = _raw_data_to_dataframe(SAMPLE_GROUPED_DATA, DEVICE_INFO_WITH_TIMESTAMP)
    df = parsed_sensor_data["BARO"]

    assert "press_alt_m" in df.columns
    assert df.select(polars.col("press_alt_m").first()).item() == pytest.approx(38_754.55)

    assert "press_alt_ft" in df.columns
    assert df.select(polars.col("press_alt_ft").first()).item() == pytest.approx(127_145.96)


def test_dataframe_conversion_row_length_mismatch_raises() -> None:
    sample_data = {
        "BARO": [[0.0, 1, 2, 3, 4, 5, 6, 7], [0.05, 1, 2, 3, 4, 5, 6, 7], [0.1, 1, 2, 3, 4, 5, 6]]
    }
    with pytest.raises(RawLogParseError) as e:
        _raw_data_to_dataframe(sample_data, DEVICE_INFO_WITH_TIMESTAMP)

    err_str = str(e.value)
    assert "BARO" in err_str
    assert "t~=0.10" in err_str
    assert "contains: 7, expected: 8" in err_str


IMU_SENSOR_INFO = SensorInfo(
    columns=["time", "wx", "wy", "wz", "ax", "ay", "az", "temperature"],
    units=["s", "deg/s", "deg/s", "deg/s", "g", "g", "g", "deg C"],
    id_="IMU",
)

IMU_INFO_WITH_TIMESTAMP = FlysightV2(
    firmware_version="abc123",
    device_id="abc123",
    session_id="abc123",
    sensor_info={"IMU": IMU_SENSOR_INFO},
    first_sensor_timestamp=0.5,
)

SAMPLE_IMU_DATA = {"IMU": [[0.01, 0, 0, 0, 1, 2, 3, 26.26]]}


def test_dataframe_derived_imu_data() -> None:
    parsed_sensor_data = _raw_data_to_dataframe(SAMPLE_IMU_DATA, IMU_INFO_WITH_TIMESTAMP)
    df = parsed_sensor_data["IMU"]

    assert "total_accel" in df.columns
    assert df.select(polars.col("total_accel").first()).item() == pytest.approx(14 ** (1 / 2))


def test_dataframe_no_derived_passthrough() -> None:
    # Just need a dummy df for this, passthrough shouldn't need any specific device info
    df = polars.DataFrame({"a": [1, 2], "b": [3, 4]})
    passthrough = _calculate_derived_columns(df, "abcd", DEVICE_INFO_WITH_TIMESTAMP)
    assert_frame_equal(df, passthrough)


def test_v2_sensor_file_parsing() -> None:
    sensor_filepath = SAMPLE_DATA_DIR / "24-04-20/04-20-00/SENSOR.CSV"
    sensor_data, device_info = parse_v2_sensor_data(sensor_filepath)

    # Actual parsing already tested upstream, don't need to repeat
    assert "IMU" in sensor_data
    assert device_info.device_id == "003e0038484e501420353131"


def test_v2_track_file_parsing() -> None:
    track_filepath = SAMPLE_DATA_DIR / "24-04-20/04-20-00/TRACK.CSV"
    track_data, device_info = parse_v2_track_data(track_filepath)

    # Actual parsing already tested upstream, don't need to repeat
    assert track_data.shape == (1, 13)
    assert device_info.device_id == "003e0038484e501420353131"


def test_directory_pipeline_no_sensor_raises(tmp_path: Path) -> None:
    track_log = tmp_path / "TRACK.CSV"
    track_log.write_text("")
    with pytest.raises(ValueError, match="SENSOR.CSV"):
        parse_v2_log_directory(tmp_path)


def test_directory_pipeline_no_track_raises(tmp_path: Path) -> None:
    track_log = tmp_path / "SENSOR.CSV"
    track_log.write_text("")
    with pytest.raises(ValueError, match="TRACK.CSV"):
        parse_v2_log_directory(tmp_path)


def test_directory_pipeline() -> None:
    data_directory = SAMPLE_DATA_DIR / "24-04-20/04-20-00"
    data_log = parse_v2_log_directory(data_directory)

    # Actual parsing already tested upstream, don't need to repeat
    assert data_log.track_data.shape == (1, 14)
    assert "IMU" in data_log.sensor_data
    assert data_log.device_info.device_id == "003e0038484e501420353131"


def test_directory_pipeline_normalize_gps() -> None:
    data_directory = SAMPLE_DATA_DIR / "24-04-20/04-20-00"
    data_log = parse_v2_log_directory(data_directory, normalize_gps=True)

    # Normalization helper tested elsewhere, just check here that the flag is being acted on
    assert data_log.track_data["lat"][0] == pytest.approx(0)
    assert data_log.track_data["lon"][0] == pytest.approx(0)


def test_v2_flightlog_normalize_gps() -> None:
    data_directory = SAMPLE_DATA_DIR / "24-04-20/04-20-00"

    # Have already tested that the coordinate is correctly parsed
    data_log = parse_v2_log_directory(data_directory, normalize_gps=False)

    data_log.normalize_gps()
    assert data_log.track_data["lat"][0] == pytest.approx(0)
    assert data_log.track_data["lon"][0] == pytest.approx(0)


def test_time_sync_delta_calculation() -> None:
    track_data = polars.DataFrame(
        {
            "time": [dt.datetime(year=2024, month=4, day=20)],
        }
    )
    time_sensor = polars.DataFrame(
        {
            "tow": [518400],
            "week": [2310],
            "elapsed_time": [1.0],
        }
    )

    track_offset = calculate_sync_delta(track_data, time_sensor)
    assert track_offset == pytest.approx(1)


def test_directory_pipeline_inserts_sync_column() -> None:
    data_directory = SAMPLE_DATA_DIR / "24-04-20/04-20-00"
    data_log = parse_v2_log_directory(data_directory)

    assert "elapsed_time_sensor" in data_log.track_data.columns
    assert data_log.track_data["elapsed_time_sensor"][0] == pytest.approx(1)


def test_directory_pipeline_prefer_parsed() -> None:
    data_directory = SAMPLE_DATA_DIR / "24-04-20/04-20-00"

    # Deserialization already tested elsewhere, so just see that this doesn't fail
    _ = parse_v2_log_directory(data_directory, prefer_processed=True)


def test_directory_pipeline_prefer_parsed_no_parsed_continues(
    capsys: pytest.CaptureFixture,
) -> None:
    data_directory = SAMPLE_DATA_DIR / "24-04-20/10-10-00"
    _ = parse_v2_log_directory(data_directory, prefer_processed=True)

    # Log parsing already tested elsewhere, so here just see if we've captured the relevant error
    captured = capsys.readouterr()
    assert "raw logging session" in captured.out
