from pathlib import Path

import polars
import pytest
from polars.testing import assert_frame_equal

from pyflysight import FlysightType, NUMERIC_T
from pyflysight.exceptions import MultipleChildLogsError, NoLogsFoundError
from pyflysight.flysight_proc import load_flysight, parse_v2_track_data
from pyflysight.log_utils import (
    classify_log_dir,
    get_idx,
    iter_log_dirs,
    locate_log_subdir,
    normalize_gps_location,
    normalize_gps_location_plaintext,
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
    with pytest.raises(NoLogsFoundError):
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
    with pytest.raises(NoLogsFoundError):
        locate_log_subdir(tmp_path, FlysightType.VERSION_1)

    with pytest.raises(NoLogsFoundError):
        locate_log_subdir(tmp_path, FlysightType.VERSION_2)


def test_locate_log_subdir_multiple_logs_raises(tmp_path: Path) -> None:
    log_a = tmp_path / "a"
    log_a.mkdir()
    (log_a / "SENSOR.CSV").touch()

    log_b = tmp_path / "b"
    log_b.mkdir()
    (log_b / "SENSOR.CSV").touch()

    with pytest.raises(MultipleChildLogsError):
        locate_log_subdir(tmp_path, FlysightType.VERSION_1)

    with pytest.raises(MultipleChildLogsError):
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
    "TEMP/0000": ("RAW.UBX", "SENSOR.CSV", "TRACK.CSV"),
}

ITER_DIR_TEST_CASES = (
    (None, {"24-04-20", "12-34-00"}),
    (FlysightType.VERSION_1, {"24-04-20"}),
    (FlysightType.VERSION_2, {"12-34-00"}),
)


@pytest.mark.parametrize(("hw_type", "truth_parent_dirnames"), ITER_DIR_TEST_CASES)
def test_iter_dir_ignore_temp(
    tmp_path: Path, hw_type: FlysightType | None, truth_parent_dirnames: set[str]
) -> None:
    for log_dirname, filenames in ITER_DIR_STRUCTURE.items():
        log_dir = tmp_path / log_dirname
        log_dir.mkdir(parents=True)

        for name in filenames:
            (log_dir / name).touch()

    found_dirs = iter_log_dirs(top_dir=tmp_path, flysight_type=hw_type, include_temp=False)
    found_dirnames = {ld.log_dir.name for ld in found_dirs}
    assert found_dirnames == truth_parent_dirnames


def test_iter_dir_include_temp(tmp_path: Path) -> None:
    for log_dirname, filenames in ITER_DIR_STRUCTURE.items():
        log_dir = tmp_path / log_dirname
        log_dir.mkdir(parents=True)

        for name in filenames:
            (log_dir / name).touch()

    # iter_log_dir doesn't currently have any logic related to the temp directory that includes a
    # hardware type filter so won't bother iterating through again
    truth_parent_dirnames = {"24-04-20", "12-34-00", "0000"}
    found_dirs = iter_log_dirs(top_dir=tmp_path, flysight_type=None, include_temp=True)
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
    assert_frame_equal(normalized_track, truth_normal)


SAMPLE_V1_TRACK = """\
time,lat,lon,hMSL,velN,velE,velD,hAcc,vAcc,sAcc,heading,cAcc,gpsFix,numSV
,(deg),(deg),(m),(m/s),(m/s),(m/s),(m),(m),(m/s),(deg),(deg),,
2021-04-20T12:34:20.00Z,33.0,-117.0,15.060,-0.63,0.98,0.29,207.635,481.468,7.15,0.0,180.0,3,4
2021-04-20T12:34:20.20Z,34.0,-115.0,15.060,-0.63,0.98,0.29,207.635,481.468,7.15,0.0,180.0,3,4
"""

# Shared between V1 & V2 tests
TRUTH_PLAINTEXT_NORMALIZED = polars.DataFrame(
    {
        "lat": [0.0, 1.0],
        "lon": [0.0, 2.0],
    }
)


def test_gps_normalize_plaintext_fsv1(tmp_path: Path) -> None:
    log_data = tmp_path / "24-04-20.CSV"
    log_data.write_text(SAMPLE_V1_TRACK)

    normalize_gps_location_plaintext(log_data, FlysightType.VERSION_1)

    converted_log = load_flysight(log_data)
    assert_frame_equal(converted_log.track_data[("lat", "lon")], TRUTH_PLAINTEXT_NORMALIZED)


SAMPLE_V2_TRACK = """\
$FLYS,1
$VAR,FIRMWARE_VER,v2024.05.25.pairing_request
$VAR,DEVICE_ID,003e0038484e501420353131
$VAR,SESSION_ID,3e10c2f6b1ea4604758b8926
$COL,GNSS,time,lat,lon,hMSL,velN,velE,velD,hAcc,vAcc,sAcc,numSV
$UNIT,GNSS,,deg,deg,m,m/s,m/s,m/s,m,m,m/s,
$DATA
$GNSS,2024-04-20T04:20:00.00Z,33.0,-117.0,630.077,-31.92,48.42,-34.93,136.117,170.718,4.74,4
$GNSS,2024-04-20T04:20:20.00Z,34.0,-115.0,630.077,-31.92,48.42,-34.93,136.117,170.718,4.74,4
"""


def test_gps_normalize_plaintext_fsv2(tmp_path: Path) -> None:
    log_data = tmp_path / "24-04-20.CSV"
    log_data.write_text(SAMPLE_V2_TRACK)

    normalize_gps_location_plaintext(log_data, FlysightType.VERSION_2)

    converted_log, _ = parse_v2_track_data(log_data)
    assert_frame_equal(converted_log[("lat", "lon")], TRUTH_PLAINTEXT_NORMALIZED)


def test_gps_normalize_plaintext_inplace_no_copy(tmp_path: Path) -> None:
    log_data = tmp_path / "24-04-20.CSV"
    log_data.write_text(SAMPLE_V2_TRACK)
    normalize_gps_location_plaintext(log_data, FlysightType.VERSION_2, inplace=True)

    assert not list(tmp_path.glob("TRACK_old.CSV"))
