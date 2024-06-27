from enum import StrEnum
from pathlib import Path

from matplotlib_window.window import flexible_window

from pyflysight.flysight_proc import parse_v2_log_directory
from pyflysight.log_utils import get_idx, trim_data_file


class TrimBy(StrEnum):  # noqa: D101
    PRESSURE_ALTITUDE = "press_alt"
    TRACK = "track"


def windowtrim_flight_log(log_dir: Path, trim_by: TrimBy = TrimBy.PRESSURE_ALTITUDE) -> None:
    flight_log = parse_v2_log_directory(log_dir)

    if trim_by == TrimBy.PRESSURE_ALTITUDE:
        df = flight_log.sensor_data["BARO"]
        xdata = df["elapsed_time"].to_list()
        ydata = df["press_alt_ft"].to_list()
    elif trim_by == TrimBy.TRACK:
        raise NotImplementedError
    else:
        raise ValueError(f"Unsupported trim by data source specified: '{trim_by}'")

    l_bound, r_bound = flexible_window(x_data=xdata, y_data=ydata, position=10, window_width=20)

    sensor_l_idx = get_idx(df, l_bound)
    sensor_r_idx = get_idx(df, r_bound)
    trim_data_file(
        source_filepath=flight_log.sensor_filepath,
        start_idx=sensor_l_idx,
        end_idx=sensor_r_idx,
        hardware_type=flight_log.device_info.flysight_type,
    )

    track_l_idx = get_idx(flight_log.track_data, l_bound)
    track_r_idx = get_idx(flight_log.track_data, r_bound)
    trim_data_file(
        source_filepath=flight_log.track_filepath,
        start_idx=track_l_idx,
        end_idx=track_r_idx,
        hardware_type=flight_log.device_info.flysight_type,
    )
