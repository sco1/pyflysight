import polars
from polars.testing import assert_frame_equal

from pyflysight.flysight_proc import FlysightV2, FlysightV2FlightLog, SensorInfo

SAMPLE_DEVICE_INFO = FlysightV2(
    firmware_version="a",
    device_id="b",
    session_id="c",
    sensor_info={"SENSOR": SensorInfo(columns=["b"], units=["c"], id_="SENSOR")},
)

SAMPLE_TRACK_DF = polars.DataFrame(
    {
        "elapsed_time": [0, 1, 2, 3, 4, 5],
        "a": [0, 1, 2, 3, 4, 5],
    }
)
TRUTH_TRACK_TRIMMED = polars.DataFrame(
    {
        "elapsed_time": [0, 1],
        "a": [2, 3],
    }
)

SAMPLE_SENSOR_DF = polars.DataFrame(
    {
        "elapsed_time": [0, 1, 2, 3, 4, 5],
        "b": [0, 1, 2, 3, 4, 5],
    }
)
TRUTH_SENSOR_TRIMMED = polars.DataFrame(
    {
        "elapsed_time": [0, 1],
        "b": [2, 3],
    }
)


def test_log_trim() -> None:
    flight_log = FlysightV2FlightLog(
        track_data=SAMPLE_TRACK_DF,
        sensor_data={"SENSOR": SAMPLE_SENSOR_DF},
        device_info=SAMPLE_DEVICE_INFO,
    )
    flight_log.trim_log(2, 4)

    assert_frame_equal(flight_log.track_data, TRUTH_TRACK_TRIMMED)
    assert_frame_equal(flight_log.sensor_data["SENSOR"], TRUTH_SENSOR_TRIMMED)

    assert flight_log._is_trimmed is True
