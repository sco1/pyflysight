import polars as pl
import pytest

from pyflysight.flysight_proc import FlysightV2, FlysightV2FlightLog, SensorInfo


@pytest.fixture
def dummy_flysight_v2() -> FlysightV2FlightLog:
    device_info = FlysightV2(
        firmware_version="a",
        device_id="b",
        session_id="c",
        sensor_info={"SENSOR": SensorInfo(columns=["a"], units=["b"], id_="SENSOR")},
    )

    imu_df = pl.DataFrame(
        {
            "ax": [1.0, 2.0],
            "ay": [3.0, 4.0],
            "az": [5.0, 6.0],
        }
    )

    baro_df = pl.DataFrame(
        {
            "pressure": [101_000.0, 100_000.0],
        }
    )

    return FlysightV2FlightLog(
        track_data=pl.DataFrame({"foo": [1]}),  # Don't care about track data here
        sensor_data={"IMU": imu_df, "BARO": baro_df},
        device_info=device_info,
    )
