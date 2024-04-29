from collections import defaultdict
from pathlib import Path

import polars


def _calc_derived_vals(flog: polars.DataFrame) -> polars.DataFrame:
    """
    Calculate derived columns from the provided flight log data.

    The following derived columns are added to the output `DataFrame`:
        * `elapsed_time`
        * `groundspeed` (m/s)
    """
    flog = flog.with_columns(
        [
            ((flog["time"] - flog["time"][0]).dt.total_milliseconds() / 1000).alias("elapsed_time"),
            ((flog["velN"] ** 2 + flog["velE"] ** 2).pow(1 / 2)).alias("groundspeed"),
        ]
    )

    return flog


def load_flysight(filepath: Path) -> polars.DataFrame:
    """
    Parse the provided FlySight log into a `DataFrame`.

    FlySight logs are assumed to contain 2 header rows, one for labels and the other for units. By
    default, the units row is discarded.

    The following derived columns are added to the output `DataFrame`:
        * `elapsed_time`
        * `groundspeed` (m/s)
    """
    flight_log = polars.read_csv(filepath, skip_rows_after_header=1)
    flight_log = flight_log.with_columns(flight_log["time"].str.to_datetime())
    flight_log = _calc_derived_vals(flight_log)

    return flight_log


def batch_load_flysight(
    top_dir: Path, pattern: str = r"*.CSV"
) -> dict[str, dict[str, polars.DataFrame]]:
    """
    Batch parse a directory of FlySight logs into a dictionary of `DataFrame`s.

    Because the FlySight hardware groups logs by date & the log CSV name does not contain date
    information, the date is inferred from the log's parent directory name & the output dictionary
    is of the form `{log date: {log_time: DataFrame}}`.

    Log file discovery is not recursive by default, the `pattern` kwarg can be adjusted to support
    a recursive glob.

    NOTE: File case sensitivity is deferred to the OS; `pattern` is passed to glob as-is so matches
    may or may not be case-sensitive.
    """
    parsed_logs: dict[str, dict[str, polars.DataFrame]] = defaultdict(dict)
    for log_file in top_dir.glob(pattern):
        # Log files are grouped by date, need to retain this since it's not in the CSV filename
        log_date = log_file.parent.stem
        parsed_logs[log_date][log_file.stem] = load_flysight(log_file)

    return parsed_logs
