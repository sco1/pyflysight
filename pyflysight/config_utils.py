from __future__ import annotations

import inspect
import io
import json
import typing as t
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from pyflysight import config_params as cp


def _write_headers(buff: io.StringIO, settings: cp.FlysightSetting) -> None:  # noqa: D101
    buff.write(f"{settings._header}\n")
    if settings._header_text is not None:
        buff.write(settings._header_text)


@dataclass
class FlysightConfig:  # noqa: D101
    def to_file(self, filepath: Path) -> None:  # noqa: D102
        buff = io.StringIO(newline="")
        buff.write(cp.FILE_HEADER)
        buff.write("\n")

        for setting_f in fields(self):
            setting: cp.FlysightSetting | list[cp.FlysightSetting] = getattr(self, setting_f.name)

            if isinstance(setting, list):
                _write_headers(buff, setting[0])
                for i, chunk in enumerate(setting, start=1):
                    chunk.to_buffer(buff)

                    # Newline delimit windows but do not add an extra newline at the end
                    if i < len(setting):
                        buff.write("\n")
            else:
                _write_headers(buff, setting)
                setting.to_buffer(buff)

            buff.write("\n")

        # A little around-fuckery to ensure only one trailing newline
        filepath.write_text(buff.getvalue().removesuffix("\n"))

    def to_json(self, filepath: Path) -> None:  # noqa: D102
        with filepath.open("w") as f:
            json.dump(asdict(self), f, indent=4)


def _remap_fields(
    parent_class: type[FlysightConfig], in_json: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Re-initialize nested config dataclasses from the provided raw json."""
    factory_map = {f.name: f.default_factory for f in fields(parent_class)}
    converted_fields = {}
    for k, v in in_json.items():
        if k not in factory_map:
            raise ValueError(f"Field '{k}' not found as field of {parent_class.__name__}")

        if inspect.isclass(factory_map[k]):
            # Non-windowed config fields will have a default factory that's just the config class,
            # so we can pass the args directly
            converted_fields[k] = factory_map[k](**v)  # type: ignore[misc]
        elif inspect.ismethod(factory_map[k]):  # pragma: no branch
            # Config window fields use a classmethod as the default factory to initialize a list
            # with the default window config, so we have to grab the parent class from this method
            # and then can reconstitute the list of windows
            pc = factory_map[k].__self__  # type: ignore[union-attr]
            converted_fields[k] = [pc(**w) for w in v]

    return converted_fields


@dataclass(slots=True)
class FlysightV2Config(FlysightConfig):
    """
    Helper representation for the FlySight Hardware Version 2 configuration parameters.

    Valid parameters are enumerated & collected, along with their defaults, by the members of
    `pyflysight.config_params`. A best attempt is made to synchronize the expected configuration
    parameters with what is available to the device firmware. Firmware changes may cause these to
    go out of sync.

    See:
      * https://flysight.ca/wiki/index.php?title=Configuring_FlySight
      * https://github.com/flysight/flysight-2-firmware

    Warning:
        The FlySight support wiki and firmware source may not be synchronized, in these cases an
        attempt is made to match the behavior described by the firmware source code.

    Info:
        While most configuration parameters are set in the device's `CONFIG.TXT`, located at the
        root of the device, there are a few configuration variables set by `FLYSIGHT.TXT` that are
        not enumerated here. These are mostly hardware-specific configuration values (e.g. charging
        amperage) and are not related to regular use of the device.
    """

    # Fields are defined in the order we want them to appear
    gps_settings: cp.GPSSettings = field(default_factory=cp.GPSSettings)
    imu_settings: cp.IMUSettings = field(default_factory=cp.IMUSettings)
    tone_settings: cp.ToneSettings = field(default_factory=cp.ToneSettings)
    threshold_settings: cp.ThresholdSettings = field(default_factory=cp.ThresholdSettings)
    rate_settings: cp.RateSettings = field(default_factory=cp.RateSettings)
    speech_settings: cp.SpeechSettings = field(default_factory=cp.SpeechSettings)
    misc_settings: cp.MiscellaneousSettings = field(default_factory=cp.MiscellaneousSettings)
    init_settings: cp.InitializationSettings = field(default_factory=cp.InitializationSettings)
    alarm_settings: cp.AlarmSettings = field(default_factory=cp.AlarmSettings)
    alarm_windows: list[cp.AlarmWindowSettings] = field(
        default_factory=cp.AlarmWindowSettings.factory
    )
    alt_settings: cp.AltitudeSettings = field(default_factory=cp.AltitudeSettings)
    silence_windows: list[cp.SilenceWindowSettings] = field(
        default_factory=cp.SilenceWindowSettings.factory
    )

    @classmethod
    def from_json(cls, filepath: Path) -> FlysightV2Config:
        """
        Create a new instance from a previously serialized configuration.

        Info:
            Configuration files serialized from a V1 device configuration will return a valid
            instance, where any V2-specific parameters (e.g. IMU settings) will be set to their
            default values.
        """
        with filepath.open("r") as f:
            config_d = json.load(f)

        fixed_fields = _remap_fields(cls, config_d)
        return cls(**fixed_fields)


@dataclass(slots=True)
class FlysightV1Config(FlysightConfig):
    """
    Helper representation for the FlySight Hardware Version 1 configuration parameters.

    Valid parameters are enumerated & collected, along with their defaults, by the members of
    `pyflysight.config_params`. A best attempt is made to synchronize the expected configuration
    parameters with what is available to the device firmware. Firmware changes may cause these to
    go out of sync.

    See:
     * https://flysight.ca/wiki/index.php?title=Configuring_FlySight
     * https://github.com/flysight/flysight

    Warning:
        The FlySight support wiki and firmware source may not be synchronized, in these cases an
        attempt is made to match the behavior described by the firmware source code.

    Info:
        While most configuration parameters are set in the device's `CONFIG.TXT`, located at the
        root of the device, there are a few configuration variables set by `FLYSIGHT.TXT` that are
        not enumerated here. These are mostly hardware-specific configuration values (e.g. charging
        amperage) and are not related to regular use of the device.
    """

    # Fields are defined in the order we want them to appear
    gps_settings: cp.GPSSettings = field(default_factory=cp.GPSSettings)
    tone_settings: cp.ToneSettings = field(default_factory=cp.ToneSettings)
    threshold_settings: cp.ThresholdSettings = field(default_factory=cp.ThresholdSettings)
    rate_settings: cp.RateSettings = field(default_factory=cp.RateSettings)
    speech_settings: cp.SpeechSettings = field(default_factory=cp.SpeechSettings)
    misc_settings: cp.MiscellaneousSettings = field(default_factory=cp.MiscellaneousSettings)
    init_settings: cp.InitializationSettings = field(default_factory=cp.InitializationSettings)
    alarm_settings: cp.AlarmSettings = field(default_factory=cp.AlarmSettings)
    alarm_windows: list[cp.AlarmWindowSettings] = field(
        default_factory=cp.AlarmWindowSettings.factory
    )
    alt_settings: cp.AltitudeSettings = field(default_factory=cp.AltitudeSettings)
    silence_windows: list[cp.SilenceWindowSettings] = field(
        default_factory=cp.SilenceWindowSettings.factory
    )

    @classmethod
    def from_json(cls, filepath: Path) -> FlysightV1Config:
        """
        Create a new instance from a previously serialized configuration.

        Warning:
            Configuration files generated for a V2 device will raise a `TypeError` due to the extra
            configuration parameters present.
        """
        with filepath.open("r") as f:
            config_d = json.load(f)

        fixed_fields = _remap_fields(cls, config_d)
        return cls(**fixed_fields)


def parse_config_params(config_filepath: Path) -> dict[str, str]:
    """
    Parse raw configuration parameters from the provided file.

    Parameters are assumed to be `param:val` pairs & are returned in their raw form. `;` is treated
    as a comment character & any text following it in a line is ignored.
    """
    parsed_params = {}
    with config_filepath.open("r") as f:
        for line in f:
            if not line.strip() or line.startswith(";"):
                continue

            kv_pair = line.split(";")[0].strip()
            if kv_pair:
                param, val = kv_pair.split(":")
                parsed_params[param] = val.strip()

    return parsed_params
