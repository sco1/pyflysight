import io
from dataclasses import dataclass
from pathlib import Path

from pyflysight.config_params import FlysightSetting
from pyflysight.config_utils import FlysightV1Config, FlysightV2Config
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


TRUTH_DEFAULT_CONFIG_V1 = SAMPLE_DATA_DIR / "config/GENERATED_V1_DEFAULT_CONFIG.TXT"


def test_default_settings_dump_v1(tmp_path: Path) -> None:
    fsc = FlysightV1Config()
    conf = tmp_path / "CONFIG.TXT"
    fsc.to_file(conf)

    assert conf.read_text() == TRUTH_DEFAULT_CONFIG_V1.read_text()


TRUTH_DEFAULT_CONFIG_V2 = SAMPLE_DATA_DIR / "config/GENERATED_V2_DEFAULT_CONFIG.TXT"


def test_default_settings_dump_v2(tmp_path: Path) -> None:
    fsc = FlysightV2Config()
    conf = tmp_path / "CONFIG.TXT"
    fsc.to_file(conf)

    assert conf.read_text() == TRUTH_DEFAULT_CONFIG_V2.read_text()
