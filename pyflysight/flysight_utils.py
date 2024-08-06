import shutil
import time
import typing as t
from collections import abc
from pathlib import Path

import psutil

from pyflysight import FlysightType
from pyflysight.config_utils import FlysightConfig, parse_config_params
from pyflysight.log_utils import iter_log_dirs


class NoDeviceStateError(ValueError): ...  # noqa: D101


class UnknownDeviceError(ValueError): ...  # noqa: D101


def iter_flysight_drives() -> abc.Generator[Path, None, None]:
    """
    Iterate through the system's mounted disk partitions and yield likely FlySight devices.

    FlySight devices should have a `FLYSIGHT.TXT` file in their root directory.

    NOTE: If called immediately after a device is plugged in (e.g. if being called in a polling
    loop), the OS may still be completing other tasks prior to assigning the device its actual drive
    letter. While in this state, attempts to read from the device will raise an `OSError`.
    """
    for p in psutil.disk_partitions():
        mount = Path(p.mountpoint)
        if tuple(mount.glob("FLYSIGHT.TXT")):
            yield mount


def get_flysight_drives() -> tuple[Path]:
    """
    Return a tuple of mounted disk partitions that are likely FlySight devices.

    FlySight devices should have a `FLYSIGHT.TXT` file in their root directory.

    NOTE: If called immediately after a device is plugged in (e.g. if being called in a polling
    loop), the OS may still be completing other tasks prior to assigning the device its actual drive
    letter. While in this state, attempts to read from the device will raise an `OSError`.
    """
    return tuple(iter_flysight_drives())  # type: ignore[return-value]


def wait_for_flysight(
    timeout: int = 10,
    polling_interval: float = 0.01,
    verbose: bool = True,
    raise_on_timeout: bool = False,
) -> tuple[Path]:
    """
    Poll the system for likely FlySight devices.

    FlySight devices should have a `FLYSIGHT.TXT` file in their root directory.

    While running, the system will be polled every `polling_interval` seconds for likely devices,
    timing out after `timeout` seconds. A `TimeoutError` may be optionally raised by setting the
    `raise_on_timeout` flag to `True`.

    Status messages may be suppressed by setting `verbose` to `False`.
    """
    if verbose:
        print("Waiting for FlySight drive(s)...")

    start_time = time.monotonic()
    while (time.monotonic() - start_time) <= timeout:
        # On Windows at least, the drive may be reported by psutil as a different drive letter until
        # the OS completes whatever plug-in tasks it's doing and assigns the actual drive letter.
        # Until the OS completes these tasks, attempting to read the files on the device will raise
        # an error, so we can try skipping the current polling interval to give it time to sort out
        try:
            flysight_drives = get_flysight_drives()
        except OSError:
            time.sleep(polling_interval)
            continue

        if flysight_drives:
            if verbose:
                print(f"Found {len(flysight_drives)} potential FlySight drive(s).")

            return flysight_drives

        time.sleep(polling_interval)

    timeout_s = "Timed Out. No FlySight drives identified."
    if not flysight_drives:
        if raise_on_timeout:
            raise TimeoutError(timeout_s)

        if verbose:
            print(timeout_s)

    return flysight_drives


def write_config(device_root: Path, config: FlysightConfig, backup_existing: bool = True) -> None:
    """
    Write the provided FlySight configuration to the provided directory.

    The configuration is written to `device_root/CONFIG.TXT`, if an existing configuration is
    present and `backup_existing` is true, the existing file will be renamed to `CONFIG_OLD.TXT`
    prior to writing of the new configuration; any existing configuration backup will be
    overwritten.
    """
    if (not device_root.is_dir()) or (not device_root.exists()):
        raise ValueError("Device root must be the root directory of a connected FlySight device.")

    flysight_config_filepath = device_root / "CONFIG.TXT"
    if flysight_config_filepath.exists() and backup_existing:
        backup_filepath = device_root / "CONFIG_OLD.TXT"
        shutil.copy(flysight_config_filepath, backup_filepath)

    config.to_file(flysight_config_filepath)


def classify_hardware_type(device_root: Path) -> FlysightType:
    """
    Classify the most likely FlySight type for the provided drive.

    Classification is made based on the contents of the FlySight's `FLYSIGHT.TXT` state information
    file, located at the root of the device. Based on the firmware source code for each hardware
    iteration, it appears that the contents & structure of this file differs significantly enough
    between the two hardware revisions to reliably make an accurate distinction.
    """
    state_file = device_root / "FLYSIGHT.TXT"
    if not state_file.exists():
        raise NoDeviceStateError("Could not locate FLYSIGHT.TXT in the provided directory.")

    device_state = state_file.read_text()
    if "FUS_Ver" in device_state:
        return FlysightType.VERSION_2
    elif "Firmware version" in device_state:
        return FlysightType.VERSION_1
    else:
        raise UnknownDeviceError("Could not identify hardware type.")


class FlysightMetadata(t.NamedTuple):  # noqa: D101
    flysight_type: FlysightType
    serial: str
    firmware: str
    n_logs: int


def get_device_metadata(device_root: Path) -> FlysightMetadata:
    """Parse the provided FlySight device for some descriptive metadata."""
    flysight_type = classify_hardware_type(device_root)

    config_params = parse_config_params(device_root / "FLYSIGHT.TXT")
    if flysight_type == FlysightType.VERSION_1:
        firmware_version = config_params["Firmware version"]
        serial = config_params["Processor serial number"]
    elif flysight_type == FlysightType.VERSION_2:  # pragma: no branch
        firmware_version = config_params["Firmware_Ver"]
        serial = config_params["Device_ID"]

    n_logs = len(tuple(iter_log_dirs(device_root, flysight_type=flysight_type)))

    return FlysightMetadata(
        flysight_type=flysight_type,
        serial=serial,
        firmware=firmware_version,
        n_logs=n_logs,
    )


def copy_logs(
    device_root: Path,
    dest: Path,
    filter_func: abc.Callable[[Path], bool] | None = None,
    exist_ok: bool = True,
    remove_after: bool = False,
) -> None:
    """
    Copy the log file tree from the provided device root to the specified destination directory.

    A filtering function may be optionally specified as a callable that accepts a path to a single
    directory of log files and returns `False` if the directory should not be copied.

    If `exist_ok` is `False`, an exception will be raised if the target directory already exists in
    the destination.

    If `remove_after` is `True`, the log directory will be deleted from the FlySight device after
    log data is copied to the destination.

    WARNING: `exist_ok=True` and `remove_after=True` are both destructive operations. Overwritten
    and/or deleted data will be lost permanently.
    """
    flysight_type = classify_hardware_type(device_root)
    for ld in iter_log_dirs(top_dir=device_root, flysight_type=flysight_type):
        if filter_func is not None:
            if not filter_func(ld.log_dir):
                continue

        # Since our iterator only yields the bottom-most directory, generate the parent structure so
        # we're not just dumping the log files into one big blob
        if flysight_type == FlysightType.VERSION_1:
            log_dest = dest / ld.log_dir.name
        elif flysight_type == FlysightType.VERSION_2:  # pragma: no branch
            log_dest = dest / "/".join(ld.log_dir.parts[-2:])

        shutil.copytree(ld.log_dir, log_dest, dirs_exist_ok=exist_ok)

        if remove_after:
            shutil.rmtree(ld.log_dir)


def erase_logs(device_root: Path, filter_func: abc.Callable[[Path], bool] | None = None) -> None:
    """
    Erase all log files from the provided device root.

    A filtering function may be optionally specified as a callable that accepts a path to a single
    directory of log files and returns `False` if the directory should not be erased.

    WARNING: This is a destructive operation. Data is removed permanently and cannot be recovered.
    """
    flysight_type = classify_hardware_type(device_root)
    for ld in iter_log_dirs(top_dir=device_root, flysight_type=flysight_type):
        if filter_func is not None:
            if not filter_func(ld.log_dir):
                continue

        shutil.rmtree(ld.log_dir)
