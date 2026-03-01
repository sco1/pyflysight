from pathlib import Path

from matplotlib_window.window import flexible_window

from pyflysight.flysight_proc import parse_v2_log_directory
from pyflysight.log_utils import FlysightType, classify_log_dir, get_idx


def calculate_alt_loss(log_dir: Path) -> float:
    """Simple helper utility to calculate altitude loss from a Flysight V2 flight log."""
    fs_type = classify_log_dir(log_dir)
    if fs_type != FlysightType.VERSION_2:
        raise ValueError("Only Flysight V2 logs are currently supported")

    flight_log = parse_v2_log_directory(log_dir, prefer_processed=True)
    baro_df = flight_log.sensor_data["BARO"]
    xdata = baro_df["elapsed_time"].to_list()
    ydata = baro_df["press_alt_ft"].to_list()

    l_bound, r_bound = flexible_window(x_data=xdata, y_data=ydata, position=10, window_width=20)
    l_idx = get_idx(baro_df, l_bound)
    r_idx = get_idx(baro_df, r_bound)

    delta: float = ydata[r_idx] - ydata[l_idx]
    print(f"Altitude loss: {delta:.2f} feet")

    return delta
