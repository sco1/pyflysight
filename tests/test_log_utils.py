from pathlib import Path

import polars
import pytest

from pyflysight import FlysightType, NUMERIC_T
from pyflysight.log_utils import classify_log_dir, get_idx

SAMPLE_DATAFRAME = polars.DataFrame(
    {
        "elapsed_time": [0, 1, 2, 3, 4, 5],
    }
)


def test_get_idx_no_ref_col_raises() -> None:
    with pytest.raises(ValueError, match="does not contain"):
        get_idx(log_data=SAMPLE_DATAFRAME, query=2, ref_col="foo")


GET_IDX_TEST_CASES = (
    (-1, 0),
    (0, 0),
    (0.3, 0),
    (0.5, 0),
    (0.7, 1),
    (1, 1),
    (6, 5),
)


@pytest.mark.parametrize(("query", "truth_idx"), GET_IDX_TEST_CASES)
def test_get_idx(query: NUMERIC_T, truth_idx: int) -> None:
    assert get_idx(SAMPLE_DATAFRAME, query) == truth_idx


LOG_CLASSIFICATION_TEST_CASES = (
    ({"24-04-20": ("04-20-00.CSV",)}, FlysightType.VERSION_1),
    ({"12-34-00": ("RAW.UBX", "SENSOR.CSV", "TRACK.CSV")}, FlysightType.VERSION_2),
)


@pytest.mark.parametrize(("file_structure", "truth_type"), LOG_CLASSIFICATION_TEST_CASES)
def test_log_dir_classification(
    tmp_path: Path, file_structure: dict[str, tuple[str, ...]], truth_type: FlysightType
) -> None:
    for log_dirname, filenames in file_structure.items():
        log_dir = tmp_path / log_dirname
        log_dir.mkdir()

        for name in filenames:
            f = log_dir / name
            f.touch()

    assert classify_log_dir(log_dir) == truth_type


def test_log_dir_characterization_no_csv_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No log files"):
        classify_log_dir(tmp_path)
