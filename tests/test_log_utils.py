import polars
import pytest

from pyflysight import NUMERIC_T
from pyflysight.log_utils import get_idx

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
