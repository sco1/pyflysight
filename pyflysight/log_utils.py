import typing as t
from collections import abc
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


def locate_log_subdir(top_dir: Path, flysight_type: FlysightType) -> Path:
    """
    Resolve the child log directory contained under the provided top level directory.

    NOTE: It is assumed that the provided `top_dir` contains only one valid directory of log files.

    NOTE: Directories containing trimmed log data are currently not considered.
    """
    if flysight_type == FlysightType.VERSION_1:
        query = "*.CSV"
    elif flysight_type == FlysightType.VERSION_2:  # pragma: no branch
        query = "SENSOR.CSV"

    found_files = tuple(top_dir.rglob(query))
    if not found_files:
        raise ValueError("No log files found in directory or its children.")
    elif len(found_files) > 1:
        raise ValueError(f"Multiple matching log directories found. Found: {len(found_files)}")

    return found_files[0].parent


class LogDir(t.NamedTuple):  # noqa: D101
    log_dir: Path
    flysight_type: FlysightType


def iter_log_dirs(
    top_dir: Path, flysight_type: FlysightType | None = None
) -> abc.Generator[LogDir, None, None]:
    """
    Iterate through children of the specified top level directory & yield log directories.

    A specific Flysight hardware revision can be targeted using the `flysight_type` argument; if
    specified as `None`, both hardware types will be searched for.

    NOTE: Order of yielded directories is not guaranteed.

    NOTE: Directories containing trimmed log data are currently not considered.
    """
    possible_parents = {f.parent for f in top_dir.rglob("*.CSV")}

    for p in possible_parents:
        filenames = {f.name for f in p.glob("*") if f.is_file()}

        # For now, filter out trimmed log directories
        if "device_info.json" in filenames:
            continue

        inferred_type = classify_log_dir(p)
        if (flysight_type is None) or (inferred_type == flysight_type):
            yield LogDir(p, inferred_type)
