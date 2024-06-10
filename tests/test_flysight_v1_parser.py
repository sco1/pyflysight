import datetime as dt
from pathlib import Path
from textwrap import dedent

import polars
from polars.testing import assert_frame_equal

from pyflysight import FlysightType, flysight_proc
from tests import checks

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"
BATCH_LOG_STEMS = {
    "21-04-20",
    "21-05-20",
}


def test_log_parse() -> None:
    sample_flight_log = SAMPLE_DATA_DIR / "21-04-20.CSV"  # Test log with single data row
    flight_log = flysight_proc.load_flysight(sample_flight_log)

    DERIVED_COLS = ("time", "elapsed_time", "groundspeed")
    for col_name in DERIVED_COLS:
        checks.is_col(flight_log, col_name)

    truth_dt = dt.datetime.strptime("2021-04-20T12:34:20.00Z", r"%Y-%m-%dT%H:%M:%S.%f%z")
    TRUTH_DERIVED = polars.DataFrame(
        {
            "time": [truth_dt],
            "elapsed_time": [0.0],
            "groundspeed": [1.165],
        }
    )
    assert_frame_equal(flight_log.select(DERIVED_COLS), TRUTH_DERIVED, rtol=1e-3)


def test_batch_log_parse() -> None:
    sample_log_pattern = "21*.CSV"  # Limit to a subset of the sample data
    flight_logs = flysight_proc.batch_load_flysight(SAMPLE_DATA_DIR, pattern=sample_log_pattern)

    # Check top level dir name
    assert "sample_data" in flight_logs

    # Check that the log files are loaded & keyed correctly
    assert set(flight_logs["sample_data"]) == BATCH_LOG_STEMS


SAMPLE_DATA_TO_SPLIT = dedent(
    """\
    a,b,c
    d,e,f
    1,2,3
    """
)


def test_v1_data_split() -> None:
    header, data = flysight_proc._split_sensor_data(
        SAMPLE_DATA_TO_SPLIT.splitlines(), hardware_type=FlysightType.VERSION_1
    )
    assert header == ["a,b,c", "d,e,f"]
    assert data == ["1,2,3"]
