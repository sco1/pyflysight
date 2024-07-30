import io
from dataclasses import dataclass
from pathlib import Path

from pyflysight.config_params import FlysightSetting
from pyflysight.config_utils import FlysightConfig
from tests import SAMPLE_DATA_DIR


@dataclass
class NoHeader(FlysightSetting):
    param: int = 13
    another_param: int = 2

    _header = "; Test header"


TRUTH_SETTING_STRING_DUMP = """\
param: 13
another_param: 2
"""


def test_setting_dump_to_buffer() -> None:
    buff = io.StringIO(newline="")
    NoHeader().to_buffer(buff)

    assert buff.getvalue() == TRUTH_SETTING_STRING_DUMP


TRUTH_DEFAULT_CONFIG = SAMPLE_DATA_DIR / "config/GENERATED_DEFAULT_CONFIG.TXT"


def test_default_settings_dump(tmp_path: Path) -> None:
    fsc = FlysightConfig()
    conf = tmp_path / "CONFIG.TXT"
    fsc.to_file(conf)

    assert conf.read_text() == TRUTH_DEFAULT_CONFIG.read_text()
