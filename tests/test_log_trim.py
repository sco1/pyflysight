from pathlib import Path
from textwrap import dedent

import pytest

from pyflysight import FlysightType
from pyflysight.log_utils import trim_data_file

SAMPLE_DATA_FILENAME = "log.csv"
SAMPLE_V1_DATA_FILE = dedent(
    """\
    Header
    Another header
    0
    1
    2
    3
    """
)
SAMPLE_V2_DATA_FILE = dedent(
    """\
    Header
    Another header
    $DATA
    0
    1
    2
    3
    """
)


@pytest.fixture
def trim_file_v2(tmp_path: Path) -> Path:
    log_filepath = tmp_path / SAMPLE_DATA_FILENAME
    log_filepath.write_text(SAMPLE_V2_DATA_FILE)

    return log_filepath


@pytest.fixture
def trim_file_v1(tmp_path: Path) -> Path:
    log_filepath = tmp_path / SAMPLE_DATA_FILENAME
    log_filepath.write_text(SAMPLE_V1_DATA_FILE)

    return log_filepath


def test_log_trim_negative_indices_raises(trim_file_v2: Path) -> None:
    with pytest.raises(ValueError, match="Specified indices"):
        trim_data_file(trim_file_v2, start_idx=-1)

    with pytest.raises(ValueError, match="Specified indices"):
        trim_data_file(trim_file_v2, end_idx=-1)


def test_v1_log_trim_defaults_rountrips_log(trim_file_v1: Path) -> None:
    trimmed_filepath = trim_data_file(trim_file_v1, hardware_type=FlysightType.VERSION_1)

    trimmed_data = trimmed_filepath.read_text()
    assert trimmed_data == SAMPLE_V2_DATA_FILE


def test_v2_log_trim_defaults_rountrips_log(trim_file_v2: Path) -> None:
    trimmed_filepath = trim_data_file(trim_file_v2)

    trimmed_data = trimmed_filepath.read_text()
    assert trimmed_data == SAMPLE_V2_DATA_FILE


# Only the header split is hardware specific, so we can omit duplicating the trim tests
TRUTH_SPLIT_1_TO_END = dedent(
    """\
    Header
    Another header
    $DATA
    1
    2
    3
    """
)


def test_log_trim_default_includes_end(trim_file_v2: Path) -> None:
    trimmed_filepath = trim_data_file(trim_file_v2, start_idx=1)
    trimmed_data = trimmed_filepath.read_text()
    assert trimmed_data == TRUTH_SPLIT_1_TO_END


TRUTH_SPLIT_1_TO_2 = dedent(
    """\
    Header
    Another header
    $DATA
    1
    2
    """
)


def test_log_trim_internal_slice(trim_file_v2: Path) -> None:
    trimmed_filepath = trim_data_file(trim_file_v2, start_idx=1, end_idx=2)
    trimmed_data = trimmed_filepath.read_text()
    assert trimmed_data == TRUTH_SPLIT_1_TO_2
