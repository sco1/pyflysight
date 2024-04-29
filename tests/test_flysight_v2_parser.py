from textwrap import dedent

import pytest

from pyflysight.flysight_proc import (
    SensorInfo,
    _parse_header,
    _partition_sensor_data,
    _split_v2_sensor_data,
)

SAMPLE_SPLIT_FILE = dedent(
    """\
    $UNIT,VBAT,s,volt
    $DATA
    $IMU,59970.376,-0.427,1.770,1.953,-0.01464,-0.00732,0.94287,25.64
    """
).splitlines()


def test_data_split() -> None:
    header, data = _split_v2_sensor_data(SAMPLE_SPLIT_FILE)
    assert header == ["$UNIT,VBAT,s,volt"]
    assert data == ["$IMU,59970.376,-0.427,1.770,1.953,-0.01464,-0.00732,0.94287,25.64"]


def test_data_split_no_partition_raises() -> None:
    with pytest.raises(ValueError, match="HELLO"):
        _ = _split_v2_sensor_data(SAMPLE_SPLIT_FILE, partition_keyword="$HELLO")


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
    with pytest.raises(ValueError, match="firmware"):
        _parse_header(SAMPLE_HEADER_NO_FIRMWARE)


SAMPLE_HEADER_NO_DEVICE_ID = dedent(
    """\
    $FLYS,1
    $VAR,FIRMWARE_VER,v2023.09.22
    $VAR,SESSION_ID,7e67d0e71a53d9d6486b0114
    """
).splitlines()


def test_header_missing_device_raises() -> None:
    with pytest.raises(ValueError, match="device"):
        _parse_header(SAMPLE_HEADER_NO_DEVICE_ID)


SAMPLE_HEADER_NO_SESSION_ID = dedent(
    """\
    $FLYS,1
    $VAR,FIRMWARE_VER,v2023.09.22
    $VAR,DEVICE_ID,003f0033484e501420353131
    """
).splitlines()


def test_header_missing_session_raises() -> None:
    with pytest.raises(ValueError, match="session"):
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
    with pytest.raises(ValueError, match="lacks column or unit information"):
        _parse_header(SAMPLE_HEADER_MISMATCHED_SENSOR_INFO)


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
