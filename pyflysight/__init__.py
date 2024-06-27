import typing as t
from enum import IntEnum

NUMERIC_T: t.TypeAlias = float | int


class FlysightType(IntEnum):  # noqa: D101
    VERSION_1 = 1
    VERSION_2 = 2
