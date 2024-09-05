import polars as pl
from polars.testing import assert_frame_equal

from pyflysight.flysight_proc import FlysightV2FlightLog


def test_accel_filter(dummy_flysight_v2: FlysightV2FlightLog) -> None:
    dummy_flysight_v2.filter_accel(filter_func=lambda x: x * 2)  # pragma: no branch
    truth_filtered = pl.DataFrame(
        {
            "ax_filt": [2.0, 4.0],
            "ay_filt": [6.0, 8.0],
            "az_filt": [10.0, 12.0],
            "total_accel_filt": [11.8321, 14.9666],
        }
    )

    filtered_cols = ("ax_filt", "ay_filt", "az_filt", "total_accel_filt")
    chunk = dummy_flysight_v2.sensor_data["IMU"].select(pl.col(filtered_cols))
    assert_frame_equal(chunk, truth_filtered)


def test_accel_filter_filter_derived(dummy_flysight_v2: FlysightV2FlightLog) -> None:
    dummy_flysight_v2.filter_accel(
        filter_func=lambda x: x * 2, filter_derived=True
    )  # pragma: no branch
    truth_filtered = pl.DataFrame(
        {
            "ax_filt": [2.0, 4.0],
            "ay_filt": [6.0, 8.0],
            "az_filt": [10.0, 12.0],
            "total_accel_filt": [23.6643, 29.9333],
        }
    )

    filtered_cols = ("ax_filt", "ay_filt", "az_filt", "total_accel_filt")
    chunk = dummy_flysight_v2.sensor_data["IMU"].select(pl.col(filtered_cols))
    assert_frame_equal(chunk, truth_filtered)


def test_baro_filter(dummy_flysight_v2: FlysightV2FlightLog) -> None:
    dummy_flysight_v2.filter_baro(filter_func=lambda x: x - 1_000)  # pragma: no branch
    truth_filtered = pl.DataFrame(
        {
            "pressure_filt": [100_000.0, 99_000.0],
            "press_alt_m_filt": [111.5370, 196.5099],
            "press_alt_ft_filt": [365.9306, 644.7096],
        }
    )

    filtered_cols = ("pressure_filt", "press_alt_m_filt", "press_alt_ft_filt")
    chunk = dummy_flysight_v2.sensor_data["BARO"].select(pl.col(filtered_cols))
    assert_frame_equal(chunk, truth_filtered)


def test_baro_filter_filter_derived(dummy_flysight_v2: FlysightV2FlightLog) -> None:
    dummy_flysight_v2.filter_baro(
        filter_func=lambda x: x - 1_000, filter_derived=True
    )  # pragma: no branch
    truth_filtered = pl.DataFrame(
        {
            "pressure_filt": [100_000.0, 99_000.0],
            "press_alt_m_filt": [-888.4630, -803.4901],
            "press_alt_ft_filt": [-634.0694, -355.2904],
        }
    )

    filtered_cols = ("pressure_filt", "press_alt_m_filt", "press_alt_ft_filt")
    chunk = dummy_flysight_v2.sensor_data["BARO"].select(pl.col(filtered_cols))
    assert_frame_equal(chunk, truth_filtered)
