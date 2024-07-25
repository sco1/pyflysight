from pathlib import Path

import polars

from pyflysight import FlysightType, NUMERIC_T


def get_idx(log_data: polars.DataFrame, query: NUMERIC_T, ref_col: str = "elapsed_time") -> int:
    """Return the first index of the data in `ref_col` closest to the provided `query` value."""
    if ref_col not in set(log_data.columns):
        raise ValueError(f"Log data does not contain column '{ref_col}'")

    delta = (log_data[ref_col] - query).abs()
    min_idx = delta.arg_min()

    if min_idx is None:
        # Not sure how to actually get here
        raise ValueError(f"Could not locate closest value, is the '{ref_col}' column empty?")

    return min_idx


def classify_log_dir(log_dir: Path) -> FlysightType:
    """
    Identify Flysight hardware revision based on the log directory contents.

    It is assumed that the provided log directory contains a single log session; no recursion is
    performed.

    The hueristic used is a simple one: if the directory contains a `SENSOR.CSV` file then it is
    assumed to be a Flysight V2 log sesssion, otherwise V1. Trimmed data files, if present, are not
    considered.
    """
    csv_stems = {file.stem for file in log_dir.glob("*.CSV")}
    if not csv_stems:
        raise ValueError("No log files found in provided log directory.")

    if "SENSOR" in csv_stems:
        return FlysightType.VERSION_2
    else:
        return FlysightType.VERSION_1
