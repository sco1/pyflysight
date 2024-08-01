import time
from collections import abc
from pathlib import Path

import psutil


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
