import polars

from pyflysight import NUMERIC_T


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
