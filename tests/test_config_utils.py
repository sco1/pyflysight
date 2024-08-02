import io
from dataclasses import dataclass
from pathlib import Path

import pytest

from pyflysight.config_params import FlysightSetting
from pyflysight.config_utils import FlysightV1Config, FlysightV2Config, parse_config_params
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


@pytest.mark.parametrize(("config_base",), ((FlysightV1Config,), (FlysightV2Config,)))
def test_config_json_round_trip(
    tmp_path: Path, config_base: FlysightV1Config | FlysightV2Config
) -> None:
    # Rather than deal with the headache of comparing all fields (since enums are lost), check that
    # the instance loaded from json serializes the same as the original
    out_json = tmp_path / "config.json"
    deserialized_out_json = tmp_path / "dserialized_out.json"

    fsc = config_base()  # type: ignore[operator]
    fsc.to_json(out_json)

    fsc_from_json = fsc.from_json(out_json)
    fsc_from_json.to_json(deserialized_out_json)

    assert out_json.read_text() == deserialized_out_json.read_text()


def test_v1_config_load_v2_config_raises(tmp_path: Path) -> None:
    out_json = tmp_path / "config.json"

    fsc = FlysightV2Config()
    fsc.to_json(out_json)

    with pytest.raises(TypeError):
        FlysightV1Config.from_json(out_json)


SAMPLE_CONFIG = """\
; FlySight - http://flysight.ca

; GPS settings

Model:     7     ; Dynamic model
                 ;   0 = Portable
                 ;   2 = Stationary
                 ;   3 = Pedestrian
                 ;   4 = Automotive
                 ;   5 = Sea
                 ;   6 = Airborne with < 1 G acceleration
                 ;   7 = Airborne with < 2 G acceleration
                 ;   8 = Airborne with < 4 G acceleration
Rate:      200   ; Measurement rate (ms)
"""


def test_parse_config_params(tmp_path: Path) -> None:
    cfg = tmp_path / "CONFIG.TXT"
    cfg.write_text(SAMPLE_CONFIG)

    truth_params = {
        "Model": "7",
        "Rate": "200",
    }

    assert parse_config_params(cfg) == truth_params
