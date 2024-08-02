from __future__ import annotations

import io
import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from pyflysight import config_params as cp


def _init_alarm_windows() -> list[cp.AlarmWindowSettings]:
    return [cp.AlarmWindowSettings()]


def _init_silence_window_settings() -> list[cp.SilenceWindowSettings]:
    return [cp.SilenceWindowSettings()]


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
                for chunk in setting:
                    chunk.to_buffer(buff)
            else:
                _write_headers(buff, setting)
                setting.to_buffer(buff)

            buff.write("\n")

        # A little around-fuckery to ensure only one trailing newline
        filepath.write_text(buff.getvalue().removesuffix("\n"))

    def to_json(self, filepath: Path) -> None:  # noqa: D102
        with filepath.open("w") as f:
            json.dump(asdict(self), f, indent=4)


@dataclass(slots=True)
class FlysightV2Config(FlysightConfig):
    """
    Helper representation for the FlySight Hardware Version 2 configuration parameters.

    Valid parameters are enumerated & collected, along with their defaults, by the members of
    `pyflysight.config_parameters`. A best attempt is made to synchronize the expected configuration
    parameters with what is available to the device firmware. Firmware changes may cause these to
    go out of sync.

    See:
        https://flysight.ca/wiki/index.php?title=Configuring_FlySight
        https://github.com/flysight/flysight-2-firmware

    NOTE: The FlySight support wiki and firmware source may not be synchronized, in these cases
    an attempt is made to match the behavior described by the firmware source code.

    NOTE: While most configuration parameters are set in the device's `CONFIG.TXT`, located at the
    root of the device, there are a few configuration variables set by `FLYSIGHT.TXT` that are not
    enumerated here. These are mostly hardware-specific configuration values (e.g. charging
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
    alarm_windows: list[cp.AlarmWindowSettings] = field(default_factory=_init_alarm_windows)
    alt_settings: cp.AltitudeSettings = field(default_factory=cp.AltitudeSettings)
    silence_windows: list[cp.SilenceWindowSettings] = field(
        default_factory=_init_silence_window_settings
    )

    @classmethod
    def from_json(cls, filepath: Path) -> FlysightV2Config:
        """
        Create a new instance from a previously serialized configuration.

        NOTE: Configuration files serialized from a V1 device configuration will return a valid
        instance, where any V2-specific parameters (e.g. IMU settings) will be set to their
        default values.
        """
        with filepath.open("r") as f:
            config_d = json.load(f)

        return cls(**config_d)


@dataclass(slots=True)
class FlysightV1Config(FlysightConfig):
    """
    Helper representation for the FlySight Hardware Version 1 configuration parameters.

    Valid parameters are enumerated & collected, along with their defaults, by the members of
    `pyflysight.config_parameters`. A best attempt is made to synchronize the expected configuration
    parameters with what is available to the device firmware. Firmware changes may cause these to
    go out of sync.

    See:
        https://flysight.ca/wiki/index.php?title=Configuring_FlySight
        https://github.com/flysight/flysight

    NOTE: The FlySight support wiki and firmware source may not be synchronized, in these cases
    an attempt is made to match the behavior described by the firmware source code.

    NOTE: While most configuration parameters are set in the device's `CONFIG.TXT`, located at the
    root of the device, there are a few configuration variables set by `FLYSIGHT.TXT` that are not
    enumerated here. These are mostly hardware-specific configuration values (e.g. charging
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
    alarm_windows: list[cp.AlarmWindowSettings] = field(default_factory=_init_alarm_windows)
    alt_settings: cp.AltitudeSettings = field(default_factory=cp.AltitudeSettings)
    silence_windows: list[cp.SilenceWindowSettings] = field(
        default_factory=_init_silence_window_settings
    )

    @classmethod
    def from_json(cls, filepath: Path) -> FlysightV1Config:
        """
        Create a new instance from a previously serialized configuration.

        NOTE: Configuration files generated for a V2 device will raise a `TypeError` due to the
        extra configuration parameters present.
        """
        with filepath.open("r") as f:
            config_d = json.load(f)

        return cls(**config_d)
