import typing as t
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import polars

HEADER_PARTITION_KEYWORD = "$DATA"


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


def _split_v2_sensor_data(
    data_lines: t.Sequence[str], partition_keyword: str = HEADER_PARTITION_KEYWORD
) -> tuple[list[str], list[str]]:
    """
    Split the provided data lines into their corresponding header & data sections.

    Sections are assumed to be delimited by `partition_keyword` (`"$DATA"`, by default).
    """
    for idx, d in enumerate(data_lines):
        if d.startswith(partition_keyword):
            return list(data_lines[:idx]), list(data_lines[idx + 1 :])  # noqa: E203

    raise ValueError(
        f"Could not locate line containing '{partition_keyword}', please check data file for issues."  # noqa: E501
    )


class SensorInfo(t.NamedTuple):
    """Store sensor record column & unit information, assumed to be of equal length."""

    columns: list[str]
    units: list[str]
    id_: str = ""


@dataclass
class FlysightV2:
    """
    Store device metadata for a corresponding FLysight V2 data logger.

    Sensor information is provided as a dictionary keyed by a sensor ID, assumed to be shared
    between the unit information contained in the header and each row of the sensor's records.
    """

    firmware_version: str
    device_id: str
    session_id: str
    sensor_info: dict[str, SensorInfo]


def _parse_header(header_lines: t.Sequence[str]) -> FlysightV2:
    """
    Parse the provided flysight header lines into a `FlysightV2` device info instance.

    Flysight's V2 CSV data log headers are assumed to begin with a series of device metadata
    followed by pairs of rows for sensor information.

    Device metadata is prefixed by `$VAR`, and we retain the following information:
        * `FIRMWARE_VER`
        * `DEVICE_ID`
        * `SESSION_ID`

    All other metadata is ignored.

    Following the device metadata are a series of pairs of rows describing the format of each
    sensors' record, e.g.:

    ```
    $COL,BARO,time,pressure,temperature
    $UNIT,BARO,s,Pa,deg C
    ```

    Sensor information is extracted and keyed by the sensor ID, assumed to be the second column of
    each corresponding row.
    """
    firmware_version = ""
    device_id = ""
    session_id = ""
    for idx, line in enumerate(header_lines):  # noqa: B007
        if line.startswith("$COL"):
            break

        if line.startswith("$VAR"):
            _, name, value = line.split(",")
            if name == "FIRMWARE_VER":
                firmware_version = value
            elif name == "DEVICE_ID":
                device_id = value
            elif name == "SESSION_ID":  # pragma: no branch
                session_id = value

    if not firmware_version:
        raise ValueError(
            "Could not locate device firmware version, please check data file for issues."
        )

    if not device_id:
        raise ValueError("Could not locate device ID, please check data file for issues.")

    if not session_id:
        raise ValueError("Could not locate session ID, please check data file for issues.")

    sensor_lines = deque(header_lines[idx:])
    if (len(sensor_lines) % 2) != 0:
        raise ValueError(
            "At least one sensor type lacks column or unit information, please check data file for issues."  # noqa: E501
        )

    sensor_info = {}
    while sensor_lines:
        sensor_header, sensor_units = [sensor_lines.popleft() for _ in range(2)]
        _, sensor_id, *column_strings = sensor_header.split(",")
        _, _, *unit_strings = sensor_units.split(",")

        sensor_info[sensor_id] = SensorInfo(
            columns=column_strings,
            units=unit_strings,
            id_=sensor_id,
        )

    flysight = FlysightV2(
        firmware_version=firmware_version,
        device_id=device_id,
        session_id=session_id,
        sensor_info=sensor_info,
    )
    return flysight


def _partition_sensor_data(
    data_lines: t.Sequence[str],
) -> tuple[dict[str, list[list[float]]], float]:
    """
    Group the provided sensor log record rows by their corresponding sensor identifier.

    Sensor records are assumed to be prefixed by their sensor identifier, located in the first
    column, e.g.:

    ```
    $IMU,59970.528,-0.427,-0.183,-0.488,0.01074,-0.01464,0.98144,25.66
    $BARO,59970.575,91839.73,26.47
    $MAG,59970.581,-0.778,0.741,-1.450,24.0
    ```

    Recorded values for each sensor are converted to float and each row is appended to a list in the
    order encountered in the log file.

    The value of the first row's timestamp is assumed to be the lowest time value for the data set
    and is returned to assist with calculation of elapsed logging time.
    """
    _, rts, *_ = data_lines[0].split(",")
    initial_timestamp = float(rts)

    sensor_data = defaultdict(list)
    for line in data_lines:
        key, *data = line.split(",")
        key = key.removeprefix("$")
        sensor_data[key].append([float(v) for v in data])

    return sensor_data, initial_timestamp


def parse_v2_sensor_data(
    data_lines: t.Sequence[str],
) -> tuple[FlysightV2, dict[str, polars.DataFrame]]:
    header, sensor_data = _split_v2_sensor_data(data_lines)
    device_info = _parse_header(header)
    grouped_sensor_data, first_timestamp = _partition_sensor_data(sensor_data)

    parsed_sensor_data: dict[str, polars.DataFrame] = {}
    for sensor in grouped_sensor_data.keys():
        df = polars.DataFrame(grouped_sensor_data[sensor], orient="row")

        try:
            df.columns = device_info.sensor_info[sensor].columns
        except polars.ShapeError:
            ...
        except KeyError:
            ...

        ...

    return device_info, parsed_sensor_data
