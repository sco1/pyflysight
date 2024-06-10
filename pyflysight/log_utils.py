import typing as t
from pathlib import Path

from pyflysight import FlysightType
from pyflysight.flysight_proc import HEADER_PARTITION_KEYWORD, _split_sensor_data


def trim_data_file(
    source_filepath: Path,
    start_idx: int = 0,
    end_idx: t.Optional[int] = None,
    hardware_type: FlysightType = FlysightType.VERSION_2,
    filename_suffix: str = "_trimmed",
) -> Path:
    """
    Trim the provided log file using the specified indices (`end_idx` is inclusive).

    The source log file's header is preserved & data output to a new CSV with the specified
    `filename_suffix`; the path to the trimmed file is optionally returned for downstream use. Note
    that any existing trimmed file will be overwritten.

    If no end index is specified, log file is trimmed from the start index to the end of the file.

    `hardware_type` must be accurately specified in order to accurately account for the log file's
    header.
    """
    full_log = source_filepath.read_text().splitlines()
    if hardware_type == FlysightType.VERSION_1:
        header, data_lines = _split_sensor_data(full_log, hardware_type=FlysightType.VERSION_1)
    else:
        header, data_lines = _split_sensor_data(full_log)

    header.append(f"{HEADER_PARTITION_KEYWORD}\n")

    if end_idx is None:
        end_idx = len(data_lines)

    if (start_idx < 0) or (end_idx < 0):
        raise ValueError("Specified indices must be >= 0.")

    out_filepath = source_filepath.with_name(f"{source_filepath.stem}{filename_suffix}.CSV")
    with out_filepath.open("w") as f:
        f.writelines("\n".join(header))
        f.writelines("\n".join(data_lines[start_idx : end_idx + 1]))  # Inclusive end index
        f.write("\n")

    return out_filepath
