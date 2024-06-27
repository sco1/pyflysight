from enum import StrEnum
from pathlib import Path

from matplotlib_window.window import flexible_window

from pyflysight.flysight_proc import FlysightV2FlightLog, parse_v2_log_directory


class TrimBy(StrEnum):  # noqa: D101
    PRESSURE_ALTITUDE = "press_alt"
    TRACK = "track"


def windowtrim_flight_log(
    log_dir: Path, trim_by: TrimBy = TrimBy.PRESSURE_ALTITUDE, write_csv: bool = False
) -> FlysightV2FlightLog:
    """
    Interactively window the log data from the provided log directory.

    Trimmed data may be optionally exported to CSV by setting the `write_csv` flag to `True`.
    """
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
    flight_log.trim_log(elapsed_start=l_bound, elapsed_end=r_bound)

    if write_csv:
        flight_log.to_csv(log_dir)

    return flight_log
