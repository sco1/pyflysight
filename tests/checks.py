import polars
from pytest_check import check_func


@check_func
def is_col(df: polars.DataFrame, col_name: str) -> None:
    """Assert that the specified column name is present in the given `DataFrame`."""
    assert col_name in df
