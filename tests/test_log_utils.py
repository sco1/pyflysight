from pathlib import Path

import polars
import polars.testing
import pytest

from pyflysight import FlysightType, NUMERIC_T
from pyflysight.log_utils import (
    classify_log_dir,
    get_idx,
    iter_log_dirs,
    locate_log_subdir,
    normalize_gps_location,
)

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


def test_log_dir_characterization_no_csv_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No log files"):
        classify_log_dir(tmp_path)


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
            (log_dir / name).touch()

    assert classify_log_dir(log_dir) == truth_type


def test_locate_log_subdir_no_log_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No log files"):
        locate_log_subdir(tmp_path, FlysightType.VERSION_1)

    with pytest.raises(ValueError, match="No log files"):
        locate_log_subdir(tmp_path, FlysightType.VERSION_2)


def test_locate_log_subdir_multiple_logs_raises(tmp_path: Path) -> None:
    log_a = tmp_path / "a"
    log_a.mkdir()
    (log_a / "SENSOR.CSV").touch()

    log_b = tmp_path / "b"
    log_b.mkdir()
    (log_b / "SENSOR.CSV").touch()

    with pytest.raises(ValueError, match="Multiple matching"):
        locate_log_subdir(tmp_path, FlysightType.VERSION_1)

    with pytest.raises(ValueError, match="Multiple matching"):
        locate_log_subdir(tmp_path, FlysightType.VERSION_2)


LOCATE_LOG_SUBDIR_TEST_CASES = (
    ("a/", "a"),
    ("a/b", "a/b"),
)


@pytest.mark.parametrize(("dir_structure", "truth_parent_path"), LOCATE_LOG_SUBDIR_TEST_CASES)
def test_locate_log_dir(tmp_path: Path, dir_structure: str, truth_parent_path: str) -> None:
    log_dir = tmp_path / dir_structure
    log_dir.mkdir(parents=True)
    (log_dir / "SENSOR.CSV").touch()

    truth_parent = tmp_path / truth_parent_path
    assert locate_log_subdir(tmp_path, FlysightType.VERSION_1) == truth_parent
    assert locate_log_subdir(tmp_path, FlysightType.VERSION_2) == truth_parent


ITER_DIR_STRUCTURE = {
    "24-04-20": ("04-20-00.CSV",),
    "12-34-00": ("RAW.UBX", "SENSOR.CSV", "TRACK.CSV"),
    "abc123": ("BARO.CSV", "IMU.CSV", "TRACK.CSV", "device_info.json"),
    "TEMP/0000": ("RAW.UBX", "SENSOR.CSV", "TRACK.CSV"),  # TEMP dir should be ignored
}

ITER_DIR_TEST_CASES = (
    (None, {"24-04-20", "12-34-00"}),
    (FlysightType.VERSION_1, {"24-04-20"}),
    (FlysightType.VERSION_2, {"12-34-00"}),
)


@pytest.mark.parametrize(("hw_type", "truth_parent_dirnames"), ITER_DIR_TEST_CASES)
def test_iter_dir(
    tmp_path: Path, hw_type: FlysightType | None, truth_parent_dirnames: set[str]
) -> None:
    for log_dirname, filenames in ITER_DIR_STRUCTURE.items():
        log_dir = tmp_path / log_dirname
        log_dir.mkdir(parents=True)

        for name in filenames:
            (log_dir / name).touch()

    found_dirs = iter_log_dirs(top_dir=tmp_path, flysight_type=hw_type)
    found_dirnames = {ld.log_dir.name for ld in found_dirs}
    assert found_dirnames == truth_parent_dirnames


def test_gps_normalize() -> None:
    track_df = polars.DataFrame(
        {
            "lat": [1.0, 2.0],
            "lon": [1.0, 3.0],
        }
    )

    truth_normal = polars.DataFrame(
        {
            "lat": [0.0, 1.0],
            "lon": [0.0, 2.0],
        }
    )

    normalized_track = normalize_gps_location(track_df)
    polars.testing.assert_frame_equal(normalized_track, truth_normal)
