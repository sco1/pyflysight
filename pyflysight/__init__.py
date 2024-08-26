import typing as t
from enum import IntEnum

HEADER_PARTITION_KEYWORD = "$DATA"


NUMERIC_T: t.TypeAlias = float | int


class FlysightType(IntEnum):
    """Enumerate expected FlySight hardware revisions."""

    VERSION_1 = 1
    VERSION_2 = 2
