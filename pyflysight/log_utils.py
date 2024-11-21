import io
import shutil
import typing as t
from collections import abc
from pathlib import Path

import polars

from pyflysight import FlysightType, HEADER_PARTITION_KEYWORD, NUMERIC_T
from pyflysight.exceptions import MultipleChildLogsError, NoLogsFoundError


def get_idx(log_data: polars.DataFrame, query: NUMERIC_T, ref_col: str = "elapsed_time") -> int:
    """Return the first index of the data in `ref_col` closest to the provided `query` value."""
    if ref_col not in set(log_data.columns):
        raise ValueError(f"Log data does not contain column '{ref_col}'")

    delta = (log_data[ref_col] - query).abs()
    min_idx = delta.arg_min()

    if min_idx is None:  # pragma: no cover
        # Not sure how to actually get here in real life
        raise ValueError(f"Could not locate closest value, is the '{ref_col}' column empty?")

    return min_idx


def classify_log_dir(log_dir: Path) -> FlysightType:
    """
    Identify FlySight hardware revision based on the log directory contents.

    It is assumed that the provided log directory contains a single log session; no recursion is
    performed.

    The hueristic used is a simple one: if the directory contains a `SENSOR.CSV` file then it is
    assumed to be a FlySight V2 log sesssion, otherwise V1. Trimmed data files, if present, are not
    considered.
    """
    csv_stems = {file.stem for file in log_dir.glob("*.CSV")}
    if not csv_stems:
        raise NoLogsFoundError("No log files found in provided log directory.")

    if "SENSOR" in csv_stems:
        return FlysightType.VERSION_2
    else:
        return FlysightType.VERSION_1


def locate_log_subdir(top_dir: Path, flysight_type: FlysightType) -> Path:
    """
    Resolve the child log directory contained under the provided top level directory.

    Note:
        It is assumed that the provided `top_dir` contains only one valid directory of log files.

    Note:
        Directories containing trimmed V2 log data are currently not considered.
    """
    if flysight_type == FlysightType.VERSION_1:
        query = "*.CSV"
    elif flysight_type == FlysightType.VERSION_2:  # pragma: no branch
        query = "SENSOR.CSV"

    found_files = tuple(top_dir.rglob(query))
    if not found_files:
        raise NoLogsFoundError("No log files found in directory or its children.")
    elif len(found_files) > 1:
        raise MultipleChildLogsError(
            f"Multiple matching log directories found. Found: {len(found_files)}"
        )

    return found_files[0].parent


class LogDir(t.NamedTuple):  # noqa: D101
    log_dir: Path
    flysight_type: FlysightType
    is_temp: bool = False


def iter_log_dirs(
    top_dir: Path,
    flysight_type: FlysightType | None = None,
    include_temp: bool = False,
) -> abc.Generator[LogDir, None, None]:
    """
    Iterate through children of the specified top level directory & yield log directories.

    A specific FlySight hardware revision can be targeted using the `flysight_type` argument; if
    specified as `None`, both hardware types will be searched for.

    The `include_temp` flag may be set to include logs in the FlySight V2's `./TEMP` directory. This
    can be helpful for situations where the FlySight V2 device turns off prior to finalizing its
    current logging session (e.g. battery runs out, hard ground impact).

    Note:
        Order of yielded directories is not guaranteed.

    Note:
        Directories containing trimmed log data are currently not considered.
    """
    possible_parents = {f.parent for f in top_dir.rglob("*.CSV")}

    for p in possible_parents:
        # FlySight V2 devices may have a TEMP directory that contains temporary logs, this should be
        # excluded
        if "TEMP" in p.parts:
            is_temp = True
            if not include_temp:
                continue
        else:
            is_temp = False

        filenames = {f.name for f in p.glob("*") if f.is_file()}

        # For now, filter out trimmed log directories
        if "device_info.json" in filenames:
            continue

        inferred_type = classify_log_dir(p)
        if (flysight_type is None) or (inferred_type == flysight_type):
            yield LogDir(log_dir=p, flysight_type=inferred_type, is_temp=is_temp)


def normalize_gps_location(
    track_data: polars.DataFrame, start_coord: tuple[float, float] = (0, 0)
) -> polars.DataFrame:
    """Shift parsed GPS coordinates so they begin at the provided starting location."""
    start_lat, start_lon = start_coord
    lat_delta = start_lat - track_data["lat"][0]
    lon_delta = start_lon - track_data["lon"][0]

    track_data = track_data.with_columns(
        lat=track_data["lat"] + lat_delta,
        lon=track_data["lon"] + lon_delta,
    )

    return track_data


def normalize_gps_location_plaintext(
    track_file: Path,
    flysight_type: FlysightType,
    start_coord: tuple[float, float] = (0, 0),
    inplace: bool = False,
) -> None:
    """
    Shift plaintext GPS coordinates so they begin at the provided starting location.

    If `inplace` is `True`, the existing track file will be overwritten. Otherwise, the unmodified
    track file will be copied to a new `TRACK_old.CSV` file in the same directory.

    Warning:
        Inplace modification is a destructive operation, all existing data will be lost and cannot
        be recovered.
    """
    if not inplace:
        track_copy = track_file.with_stem("TRACK_old")
        shutil.copy(track_file, track_copy)

    # Buffer one end for now, if memory usage ends up being an issue for some reason can swap to
    # using a tempfile
    buff = io.StringIO()
    with track_file.open("r") as f:
        # Write headers straight through
        if flysight_type == FlysightType.VERSION_1:
            for _ in range(2):
                buff.write(next(f))
        elif flysight_type == FlysightType.VERSION_2:  # pragma: no branch
            for line in f:  # pragma: no branch
                buff.write(line)
                if line.startswith(HEADER_PARTITION_KEYWORD):
                    break

        lat_delta = lon_delta = 0.0
        for line in f:
            comps = line.split(",")
            if flysight_type == FlysightType.VERSION_1:
                idx = (1, 2)
            elif flysight_type == FlysightType.VERSION_2:  # pragma: no branch
                idx = (2, 3)

            lat, lon = (float(comps[i]) for i in idx)

            if lat_delta == 0:
                # Calculate deltas from the first data line
                # If by extreme chance the delta still ends up being zero, buy a lottery ticket
                lat_delta = start_coord[0] - lat
                lon_delta = start_coord[1] - lon

            lat += lat_delta
            lon += lon_delta

            comps[idx[0]] = str(lat)
            comps[idx[1]] = str(lon)
            buff.write(",".join(comps))

    track_file.write_text(buff.getvalue())
