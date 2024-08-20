from __future__ import annotations

import io
from dataclasses import dataclass, fields
from enum import IntEnum

# NOTE: All dataclass field names should match the values expected by FlySight's config parser


@dataclass(slots=True)
class FlysightSetting:
    _header: str = ""
    _header_text: str | None = None

    def to_buffer(self, buff: io.StringIO) -> None:
        """
        Dump the class' fields to the provided string buffer.

        NOTE: Fields with a leading underscore are ignored.
        """
        for param in fields(self):
            if param.name.startswith("_"):
                continue

            val = getattr(self, param.name)
            buff.write(f"{param.name}: {val}\n")


FILE_HEADER = """\
; FlySight - http://flysight.ca
;
; NOTE: This log file has been automatically generated and does not contain the
;       descriptive comments found in the default configuration file as shipped
;       by the manufacturer. Firmware updates may introduce and/or remove
;       configuration values; missing values should be interpreted by the
;       FlySight config parser as their defaults. Configuration details can be
;       found in the FlySight support wiki or the firmware source repository.
;
;       See:
;           https://flysight.ca/wiki/index.php?title=Configuring_FlySight
;           https://github.com/flysight/flysight (Hardware V1)
;           https://github.com/flysight/flysight-2-firmware (Hardware V2)
;
; NOTE: Defaults are as of time of writing & may change based on firmware
;       version
"""


# GPS Settings
class GPSModel(IntEnum):
    PORTABLE = 0
    STATIONARY = 2
    PEDESTRIAN = 3
    AUTOMOTIVE = 4
    SEA = 5
    AIRBORNE_LT_1G = 6
    AIRBORNE_LT_2G = 7
    AIRBORNE_LT_4G = 8


@dataclass(slots=True)
class GPSSettings(FlysightSetting):
    Model: GPSModel = GPSModel.AIRBORNE_LT_1G
    Rate: int = 200  # milliseconds

    _header: str = "; GPS settings"


# IMU settings
IMU_HEADER = """\
; NOTE: Configuring away from default IMU values currently requires installation
;       of beta firmware, which can be found at:
;
;       https://flysight.ca/firmware/?include_beta=true
;
; NOTE: Currently not possible to achieve full logging rate for the
;       accelerometer and gyro; the currently known maximum is ~1666 Hz
"""


class BaroODR(IntEnum):
    DISABLE = 0
    HZ_1 = 1
    HZ_10 = 2
    HZ_25 = 3
    HZ_50 = 4
    HZ_75 = 5
    HZ_100 = 6
    HZ_200 = 7


class HumODR(IntEnum):
    DISABLE = 0
    HZ_1 = 1
    HZ_7 = 2
    HZ_12_5 = 3


class MagODR(IntEnum):
    HZ_10 = 0
    HZ_20 = 1
    HZ_50 = 2
    HZ_100 = 3


class AccelODR(IntEnum):
    DISABLE = 0
    HZ_12_5 = 1
    HZ_26 = 2
    HZ_52 = 3
    HZ_104 = 4
    HZ_208 = 5
    HZ_416 = 6
    HZ_833 = 7
    HZ_1666 = 8
    HZ_3333 = 9
    HZ_6666 = 10
    HZ_1_6 = 11


class AccelFS(IntEnum):
    GEE_2 = 0
    GEE_16 = 1
    GEE_4 = 2
    GEE_8 = 3


class GyroODR(IntEnum):
    DISABLE = 0
    HZ_12_5 = 1
    HZ_26 = 2
    HZ_52 = 3
    HZ_104 = 4
    HZ_208 = 5
    HZ_416 = 6
    HZ_833 = 7
    HZ_1666 = 8
    HZ_3333 = 9
    HZ_6666 = 10


class GyroFS(IntEnum):
    DEG_S_250 = 0
    DEG_S_500 = 1
    DEG_S_1000 = 2
    DEG_S_2000 = 3


@dataclass(slots=True)
class IMUSettings(FlysightSetting):
    Baro_ODR: BaroODR = BaroODR.HZ_10
    Hum_ODR: HumODR = HumODR.HZ_1
    Mag_ODR: MagODR = MagODR.HZ_10
    Accel_ODR: AccelODR = AccelODR.HZ_12_5
    Accel_FS: AccelFS = AccelFS.GEE_16
    Gyro_ODR: GyroODR = GyroODR.HZ_12_5
    Gyro_FS: GyroFS = GyroFS.DEG_S_2000

    _header: str = "; IMU settings"
    _header_text: str | None = IMU_HEADER


# Tone settings
class ToneMeasurementMode(IntEnum):
    HORIZONTAL_SPEED = 0
    VERTICAL_SPEED = 1
    GLIDE_RATIO = 2
    INVERSE_GLIDE_RATIO = 3
    TOTAL_SPEED = 4
    DIVE_ANGLE = 11


class ToneLimits(IntEnum):
    NO_TONE = 0
    MIN_MAX_TONE = 1
    CHIRP_UP_DOWN = 2
    CHIRP_DOWN_UP = 3


class ToneVolume(IntEnum):
    QUIETEST = 0
    EVEN_MORE_QUIETER = 1
    MORE_QUIETER = 2
    QUIETER = 3
    MIDDLE = 4
    LOUDER = 5
    MORE_LOUDER = 6
    EVEN_MORE_LOUDER = 7
    LOUDEST = 8


@dataclass(slots=True)
class ToneSettings(FlysightSetting):
    Mode: ToneMeasurementMode = ToneMeasurementMode.GLIDE_RATIO
    Min: int = 0
    Max: int = 300
    Limits: ToneLimits = ToneLimits.MIN_MAX_TONE
    Volume: ToneVolume = ToneVolume.MORE_LOUDER

    _header: str = "; Tone settings"


@dataclass(slots=True)
class ThresholdSettings(FlysightSetting):
    V_Thresh: int = 1000
    H_Thresh: int = 0

    _header: str = "; Thresholds"


# Rate settings
class Mode2(IntEnum):
    HORIZONTAL_SPEED = 0
    VERTICAL_SPEED = 1
    GLIDE_RATIO = 2
    INVERSE_GLIDE_RATIO = 3
    TOTAL_SPEED = 4
    MAG_VALUE_1 = 8
    CHANGE_VALUE_1 = 9
    DIVE_ANGLE = 11


class FlatLine(IntEnum):
    NO = 0
    YES = 1


@dataclass(slots=True)
class RateSettings(FlysightSetting):
    Mode_2: Mode2 = Mode2.CHANGE_VALUE_1
    Min_Val_2: int = 300
    Max_Val_2: int = 1500
    Min_Rate: int = 100
    Max_Rate: int = 500
    Flatline: FlatLine = FlatLine.NO

    _header: str = "; Rate settings"


# Speech settings
class SpeechVolume(IntEnum):
    QUIETEST = 0
    EVEN_MORE_QUIETER = 1
    MORE_QUIETER = 2
    QUIETER = 3
    MIDDLE = 4
    LOUDER = 5
    MORE_LOUDER = 6
    EVEN_MORE_LOUDER = 7
    LOUDEST = 8


class SpeechMode(IntEnum):
    HORIZONTAL_SPEED = 0
    VERTICAL_SPEED = 1
    GLIDE_RATIO = 2
    INVERSE_GLIDE_RATIO = 3
    TOTAL_SPEED = 4
    ALTITUDE_ABOVE_DZ = 5
    DIVE_ANGLE = 11


class SpeechUnits(IntEnum):
    KMH_M = 0
    MPH_F = 1


@dataclass(slots=True)
class SpeechSettings(FlysightSetting):
    Sp_Rate: int = 0
    Sp_Volume: SpeechVolume = SpeechVolume.MORE_LOUDER
    Sp_Mode: SpeechMode = SpeechMode.GLIDE_RATIO
    Sp_Units: SpeechUnits = SpeechUnits.MPH_F
    Sp_Dec: int = 1

    _header: str = "; Speech settings"


# Miscellaneous settings
class UseSAS(IntEnum):
    NO = 0
    YES = 1


@dataclass(slots=True)
class MiscellaneousSettings(FlysightSetting):
    Use_SAS: UseSAS = UseSAS.YES
    TZ_Offset: int = 0

    _header: str = "; Miscellaneous"


# Initialization settings
INITIALIZATION_HEADER = """\
; NOTE: Consult the FlySight support wiki for instructions on how to select the
;       initialization audio file:
;
;       https://flysight.ca/wiki/index.php?title=Configuring_FlySight#Selectable_configurations
"""


class InitMode(IntEnum):
    DO_NOTHING = 0
    TEST_SPEECH = 1
    PLAY_FILE = 2


@dataclass(slots=True)
class InitializationSettings(FlysightSetting):
    Init_Mode: InitMode = InitMode.DO_NOTHING
    Init_File: int = 0

    _header: str = "; Initialization"
    _header_text: str | None = INITIALIZATION_HEADER


# Alarm settings
ALARM_HEADER = """\
; NOTE: Alarms may be set for multiple altitudes by specifying repeated blocks
;       of configuration information. See the FlySight support wiki for
;       examples & instructions on selecting alarm files:
;
;       https://flysight.ca/wiki/index.php?title=Configuring_FlySight#Speech_alarms
;
; NOTE: Altitudes are specified relative to ground elevation, as specified by
;       Dz_Elev.
"""


class AlarmType(IntEnum):
    NO_ALARM = 0
    BEEP = 1
    CHIRP_UP = 2
    CHIRP_DOWN = 3
    PLAY_FILE = 4


@dataclass(slots=True)
class AlarmSettings(FlysightSetting):
    Win_Above: int = 0
    Win_Below: int = 0
    DZ_Elev: int = 0

    _header: str = "; Alarm settings"
    _header_text: str | None = ALARM_HEADER


@dataclass(slots=True)
class AlarmWindowSettings(FlysightSetting):
    Alarm_Elev: int = 0
    Alarm_Type: AlarmType = AlarmType.NO_ALARM
    Alarm_File: int = 0

    _header: str = "; Alarm windows"
    _header_text: str | None = None

    @classmethod
    def factory(cls) -> list[AlarmWindowSettings]:  # noqa: D102
        return [cls()]


# Altitude mode settings
ALTITUDE_HEADER = """\
; NOTE: Altitudes are specified relative to ground elevation, as specified by
;       Dz_Elev. Altitude mode will not function below 1500m AGL.
;
; NOTE: Altitude is called out when the FlySight first receives a GPS fix in
;       order to verify DZ_Elev is set properly. If correctly configured
;       this altitude should be within 10 meters of zero.
"""


class AltUnits(IntEnum):
    METERS = 0
    FEET = 1


@dataclass(slots=True)
class AltitudeSettings(FlysightSetting):
    Alt_Units: AltUnits = AltUnits.FEET
    Alt_Step: int = 0

    _header: str = "; Altitude mode settings"
    _header_text: str | None = ALTITUDE_HEADER


# Silence window settings
SILENCE_WINDOW_HEADER = """\
; NOTE: Multiple silence windows may be specified to silence tones during the
;       window elevation; only alarms will be audible.
;
; NOTE: Altitudes are specified relative to ground elevation, as specified by
;       Dz_Elev.
;
; NOTE: Silence windows are currently not detailed in the FlySight support wiki.
"""


@dataclass(slots=True)
class SilenceWindowSettings(FlysightSetting):
    Win_Top: int = 0
    Win_Bottom: int = 0

    _header: str = "; Silence windows"
    _header_text: str | None = SILENCE_WINDOW_HEADER

    @classmethod
    def factory(cls) -> list[SilenceWindowSettings]:  # noqa: D102
        return [cls()]


ALL_SETTINGS = (
    GPSSettings,
    IMUSettings,
    ToneSettings,
    ThresholdSettings,
    RateSettings,
    SpeechSettings,
    MiscellaneousSettings,
    InitializationSettings,
    AlarmSettings,
    AlarmWindowSettings,
    AltitudeSettings,
    SilenceWindowSettings,
)
