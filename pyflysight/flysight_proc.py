from __future__ import annotations

import datetime as dt
import json
import typing as t
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import polars

from pyflysight import FlysightType, NUMERIC_T
from pyflysight.log_utils import get_idx

HEADER_PARTITION_KEYWORD = "$DATA"

GroupedSensorData: t.TypeAlias = dict[str, list[list[float]]]
SensorDataFrames: t.TypeAlias = dict[str, polars.DataFrame]


def _calc_derived_track_vals(flog: polars.DataFrame) -> polars.DataFrame:
    """
    Calculate derived columns from the provided flight log data.

    The following derived columns are added to the output `DataFrame`:
        * `elapsed_time`
        * `groundspeed` (m/s)
    """
    flog = flog.with_columns(
        elapsed_time=((flog["time"] - flog["time"][0]).dt.total_milliseconds() / 1000),
        groundspeed=((flog["velN"] ** 2 + flog["velE"] ** 2).pow(1 / 2)),
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
    flight_log = _calc_derived_track_vals(flight_log)

    return flight_log


def batch_load_flysight(
    top_dir: Path,
    pattern: str = r"*.CSV",
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


def _split_sensor_data(
    data_lines: t.Sequence[str],
    hardware_type: FlysightType = FlysightType.VERSION_2,
    partition_keyword: str = HEADER_PARTITION_KEYWORD,
) -> tuple[list[str], list[str]]:
    """
    Split the provided data lines into their corresponding header & data sections.

    Flysight V1 sections do not have a partition keyword, but are assumed to have just 2 data lines.
    Flysight V2 sections are assumed to be delimited by `partition_keyword` (`"$DATA"`, by default).
    """
    if hardware_type == FlysightType.VERSION_1:
        return list(data_lines[:2]), list(data_lines[2::])
    else:
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

    `first_timestamp` refers to the `time` value of the first data record & used to calculate the
    running `elapsed_time` column during the parsing pipeline. This timestamp value must be set &
    should be set later by the provided parsing pipeline.

    `ground_pressure_pa` is the atmospheric pressure at ground level, in Pascals, used by some
    pressure altitude calculations. This defaults to standard day sea level pressure.
    """

    firmware_version: str
    device_id: str
    session_id: str
    sensor_info: dict[str, SensorInfo]
    flysight_type: FlysightType = FlysightType.VERSION_2

    first_timestamp: float | None = None
    ground_pressure_pa: int | float = 101_325

    @classmethod
    def from_json(cls, raw_json: dict[str, t.Any]) -> FlysightV2:
        """
        Generate a new instance from a raw device data JSON file.

        It is assumed that the JSON file is generated by `FlysightV2FlightLog.to_csv`, only minimal
        checking is done for JSON validity (top level keys match `FlysightV2`'s fields).
        """
        expected_fields = {field.name for field in fields(cls)}
        missing = expected_fields - raw_json.keys()

        if missing:
            raise ValueError(f"Missing required device info fields: {missing}")

        sensor_info = {sens: SensorInfo(*vals) for sens, vals in raw_json["sensor_info"].items()}

        return cls(
            firmware_version=raw_json["firmware_version"],
            device_id=raw_json["device_id"],
            session_id=raw_json["session_id"],
            sensor_info=sensor_info,
            flysight_type=FlysightType(raw_json["flysight_type"]),
            first_timestamp=raw_json["first_timestamp"],
            ground_pressure_pa=raw_json["ground_pressure_pa"],
        )


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
        raise ValueError("Could not locate device firmware version.")

    if not device_id:
        raise ValueError("Could not locate device ID.")

    if not session_id:
        raise ValueError("Could not locate session ID.")

    sensor_lines = deque(header_lines[idx:])
    if (len(sensor_lines) % 2) != 0:
        raise ValueError("At least one sensor type lacks column or unit information.")

    sensor_info = {}
    while sensor_lines:
        sensor_header, sensor_units = [sensor_lines.popleft() for _ in range(2)]
        _, sensor_id, *column_strings = sensor_header.split(",")
        _, _, *unit_strings = sensor_units.split(",")

        # The Flysight V2 track file does not appear to provide a unit string for its time column,
        # which is a datetime string rather than a float that the other sensor records utilize
        if sensor_id == "GNSS" and not unit_strings[0]:
            unit_strings[0] = "datetime"

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


def _partition_sensor_data(data_lines: t.Sequence[str]) -> tuple[GroupedSensorData, float]:
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


def _calculate_derived_columns(
    df: polars.DataFrame,
    sensor: str,
    device_info: FlysightV2,
) -> polars.DataFrame:
    """
    Calculate sensor-specific derived quantities for the provided `DataFrame`.

    The following columns are derived:
        * Baro
            * `pressure_altitude` - calculated as ...

    If no specific calculations are required, the `DataFrame` is passed through unchanged.
    """
    if sensor == "BARO":
        press_alt_m = (
            44_330 * (1 - (df["pressure"] / device_info.ground_pressure_pa).pow(1 / 5.225))
        ).alias("press_alt_m")
        press_alt_ft = (press_alt_m * 3.2808).alias("press_alt_ft")

        df = df.hstack([press_alt_m, press_alt_ft])

    return df


def _raw_data_to_dataframe(
    sensor_data: GroupedSensorData,
    device_info: FlysightV2,
) -> SensorDataFrames:
    """
    Convert the provided grouped sensor data into their corresponding `DataFrame`s.

    Headers are replaced using the device's metadata. It is assumed that all `DataFrame`s contain a
    `time` column, and a normalized `elapsed_time` column will be derived using the device's first
    encountered timestamp.
    """
    if device_info.first_timestamp is None:
        raise ValueError("First timestamp for logging session not specified.")

    parsed_sensor_data: dict[str, polars.DataFrame] = {}
    for sensor in sensor_data.keys():
        df = polars.DataFrame(sensor_data[sensor], orient="row")

        try:
            df.columns = device_info.sensor_info[sensor].columns
        except polars.ShapeError as e:
            n_headers = len(device_info.sensor_info[sensor].columns)
            raise ValueError(
                f"Number of column headers for {sensor} do not match the number of data columns present (expected: {df.width}, received: {n_headers})."  # noqa: E501
            ) from e
        except KeyError as e:
            raise ValueError(
                f"Could not locate column header information for {sensor} sensor."
            ) from e

        # All sensor DataFrames get elapsed time, then we can dispatch further by sensor type
        df = df.with_columns(elapsed_time=((df["time"] - device_info.first_timestamp)))
        df = _calculate_derived_columns(df=df, sensor=sensor, device_info=device_info)

        parsed_sensor_data[sensor] = df

    return parsed_sensor_data


def parse_v2_sensor_data(log_filepath: Path) -> tuple[SensorDataFrames, FlysightV2]:
    """
    Data parsing pipeline for a Flysight V2 sensor log CSV file.

    Sensor data files should come off the Flysight as `SENSOR.CSV`.
    """
    data_lines = log_filepath.read_text().splitlines()

    header, sensor_data = _split_sensor_data(data_lines)
    device_info = _parse_header(header)
    grouped_sensor_data, first_timestamp = _partition_sensor_data(sensor_data)
    device_info.first_timestamp = first_timestamp

    parsed_sensor_data = _raw_data_to_dataframe(grouped_sensor_data, device_info)

    return parsed_sensor_data, device_info


def _raw_v2_track_to_dataframe(
    sensor_data: t.Iterable[str], device_info: FlysightV2
) -> polars.DataFrame:
    """
    Convert raw GNSS track information into its corresponding `DataFrame`.

    Data is assumed to be an iterable of the raw string lines from the Flysight V2's track CSV file.

    Headers are replaced using the device's metadata. It is assumed that the first column is a UTC
    datetime, and a normalized `elapsed_time` column will be derived using the device's first
    encountered timestamp.

    A `groundspeed` column is also derived from the provided track's GPS velocity vectors.
    """
    split_log_lines = []
    for line in sensor_data:
        _, raw_timestamp, *rest, raw_n_satellites = line.split(",")
        split_log_lines.append(
            [
                dt.datetime.fromisoformat(raw_timestamp),
                *(float(n) for n in rest),
                int(raw_n_satellites),
            ]
        )

    df = polars.DataFrame(split_log_lines, orient="row")
    df.columns = device_info.sensor_info["GNSS"].columns
    df = _calc_derived_track_vals(df)

    return df


def parse_v2_track_data(log_filepath: Path) -> tuple[polars.DataFrame, FlysightV2]:
    """
    Data parsing pipeline for a Flysight V2 track log CSV file.

    Sensor data files should come off the Flysight as `TRACK.CSV`.
    """
    data_lines = log_filepath.read_text().splitlines()
    header, sensor_data = _split_sensor_data(data_lines)
    device_info = _parse_header(header)
    parsed_sensor_data = _raw_v2_track_to_dataframe(sensor_data, device_info)

    return parsed_sensor_data, device_info


@dataclass
class FlysightV2FlightLog:  # noqa: D101
    track_data: polars.DataFrame
    sensor_data: SensorDataFrames
    device_info: FlysightV2

    _is_trimmed: bool = False  # If True, then device_info.first_timestamp is likely out of sync

    def to_csv(self, base_dir: Path) -> None:
        """
        Output logged data to a collection of CSV files relative to the provided base directory.

        Sensor data is named by sensor name & nested under `base_dir`:
        `base_dir/device_id/session_id/*`. Note that any existing data in this directory will be
        overwritten.
        """
        out_dir = base_dir / f"{self.device_info.device_id}/{self.device_info.session_id}"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_filepath = out_dir / "TRACK.CSV"
        self.track_data.write_csv(out_filepath)

        for sensor_name, sensor_data in self.sensor_data.items():
            out_filepath = out_dir / f"{sensor_name}.CSV"
            sensor_data.write_csv(out_filepath)

        device_info_filepath = out_dir / "device_info.json"
        with device_info_filepath.open("w") as f:
            json.dump(asdict(self.device_info), f)

    def trim_log(self, elapsed_start: NUMERIC_T, elapsed_end: NUMERIC_T) -> None:
        """
        Trim the sensor & track logs to data between the provided start and end elapsed times.

        NOTE: The elapsed time column is re-normalized to the provided trim window.
        """
        for sensor, df in self.sensor_data.items():
            l_idx = get_idx(df, elapsed_start)
            r_idx = get_idx(df, elapsed_end)
            self.sensor_data[sensor] = df[l_idx:r_idx]

            # Re-normalize elapsed time
            new_elapsed_start = self.sensor_data[sensor]["elapsed_time"][0]
            new_time = self.sensor_data[sensor]["elapsed_time"] - new_elapsed_start
            self.sensor_data[sensor] = self.sensor_data[sensor].with_columns(elapsed_time=new_time)

        # Trim track data since it's stored separately
        l_idx = get_idx(self.track_data, elapsed_start)
        r_idx = get_idx(self.track_data, elapsed_end)
        self.track_data = self.track_data[l_idx:r_idx]

        # Re-normalize elapsed time
        new_elapsed_start = self.track_data["elapsed_time"][0]
        new_time = self.track_data["elapsed_time"] - new_elapsed_start
        self.track_data = self.track_data.with_columns(elapsed_time=new_time)

        self._is_trimmed = True

    @classmethod
    def from_csv(cls, base_dir: Path) -> FlysightV2FlightLog:
        """
        Generate a new instance from a directory of saved device data.

        The specified base directory must contain only one child directory of device data,
        determined by the presence of a `device_info.json` file.

        For example, given the file structure:

        ```
        .
        ├── a/
        │   └── b/
        │       └── device_data_1
        └── c/
            └── d/
                ├── device_data_2
                └── device_data_3
        ```

        `device_data_1` can be located using `base_dir` as `/a/`, `/a/b/`, or `/a/b/device_data_1`,
        but `device_data_2` and `device_data_3` must be located using `base_dir` as
        `/a/b/device_data_2` and `/a/b/device_data_3`, respectively.

        It is assumed that the data directory is generated by `FlysightV2FlightLog.to_csv`, minimal
        error checking is performed prior to attempting to reload the data.
        """
        device_info_filepath = list(base_dir.rglob("device_info.json"))
        if not device_info_filepath:
            raise ValueError("No device info JSON found in the given base dir or its children.")

        if len(device_info_filepath) != 1:
            raise ValueError("Must specify a base dir with only one child data directory.")

        with device_info_filepath[0].open() as f:
            raw_device_info = json.load(f)
        device_info = FlysightV2.from_json(raw_device_info)

        data_dir = device_info_filepath[0].parent
        track_data: polars.DataFrame | None = None
        sensor_data: SensorDataFrames = {}
        for sensor_filepath in data_dir.glob("*.CSV"):
            sensor = sensor_filepath.stem
            if sensor == "TRACK":
                track_data = polars.read_csv(sensor_filepath)
                track_data = track_data.with_columns(time=track_data["time"].str.to_datetime())
            else:
                sensor_data[sensor] = polars.read_csv(sensor_filepath)

        if track_data is None:
            raise ValueError("Track data file could not be located.")

        if not sensor_data:
            raise ValueError("No sensor data files could be located.")

        return cls(
            track_data=track_data,
            sensor_data=sensor_data,
            device_info=device_info,
        )


def parse_v2_log_directory(
    log_directory: Path, sensor_filename: str = "SENSOR.CSV", track_filename: str = "TRACK.CSV"
) -> FlysightV2FlightLog:
    """
    Data parsing pipeline for a directory of Flysight V2 logs.

    The Flysight V2 outputs a timestamped (`YY-mm-DD/HH-MM-SS/*`) directory of files:
        * `EVENT.CSV` - Debugging output, optionally present based on firmware version
        * `RAW.UBX` - Raw UBlox sensor output
        * `SENSOR.CSV` - Onboard sensor data
        * `TRACK.CSV` - GPS sensor data
    """
    sensor_filepath = log_directory / sensor_filename
    if not sensor_filepath.exists():
        raise ValueError(f"Could not locate 'SENSOR.CSV` in directory: '{log_directory}'")

    track_filepath = log_directory / track_filename
    if not track_filepath.exists():
        raise ValueError(f"Could not locate 'TRACK.CSV` in directory: '{log_directory}'")

    sensor_data, device_info = parse_v2_sensor_data(sensor_filepath)
    track_data, _ = parse_v2_track_data(track_filepath)
    return FlysightV2FlightLog(
        track_data=track_data,
        sensor_data=sensor_data,
        device_info=device_info,
    )
