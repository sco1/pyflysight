import typing as t
from pathlib import Path

import typer
from sco1_misc.prompts import prompt_for_dir

from pyflysight import FlysightType
from pyflysight.flysight_utils import get_device_metadata, get_flysight_drives, wait_for_flysight
from pyflysight.log_utils import classify_log_dir, iter_log_dirs
from pyflysight.trim_app import windowtrim_flight_log

pyflysight_cli = typer.Typer(add_completion=False)

device_app = typer.Typer(add_completion=False, help="FlySight device utilities.")
pyflysight_cli.add_typer(device_app, name="device")

config_app = typer.Typer(add_completion=False)
device_app.add_typer(config_app, name="config", help="Device configuration utilities.")

log_app = typer.Typer(add_completion=False, help="FlySight device log utilities.")
pyflysight_cli.add_typer(log_app, name="logs")

trim_app = typer.Typer(add_completion=False)
pyflysight_cli.add_typer(trim_app, name="trim", help="FlySight log trimming.")


def _print_connected_drives(flysight_drives: t.Iterable[Path]) -> None:
    for idx, drive in enumerate(flysight_drives):
        md = get_device_metadata(drive)
        md_str = (
            f"{idx}. {drive} - FlySight V{md.flysight_type}, Logs Available: {md.n_logs}\n"
            f"    Serial: {md.serial}\n"
            f"    Firmware: {md.firmware}"
        )
        print(md_str)


@device_app.command()
def list(wait_for: int = typer.Option(0, min=0)) -> None:
    """
    List connected Flysight devices.

    If `wait_for` is > 0, the OS will be polled for up to `wait_for` seconds for at least one
    FlySight device to be connected.
    """
    if wait_for > 0:
        flysight_drives = wait_for_flysight(timeout=wait_for)
    else:
        flysight_drives = get_flysight_drives()

    if not flysight_drives:
        # Polling function already prints its own timeout message
        if wait_for == 0:
            print("No connected FlySight devices could be identified.")
        return

    _print_connected_drives(flysight_drives)


@config_app.command()
def write_default() -> None:
    """
    Write default configuration.

    WARNING: This action is destructive. All existing configuration information & formatting will be
    permanently lost.
    """
    raise NotImplementedError


@config_app.command()
def write_from_json() -> None:
    """
    Write previously serialized paramters.

    WARNING: This action is destructive. All existing configuration information & formatting will be
    permanently lost.
    """
    raise NotImplementedError


@config_app.command()
def write_from_other() -> None:
    """
    Copy configuration from file.

    WARNING: This action is destructive. All existing configuration information & formatting will be
    permanently lost.
    """
    raise NotImplementedError


@log_app.command()
def copy() -> None:
    """Copy all logs on device to the specified destination."""
    raise NotImplementedError


@log_app.command()
def clear() -> None:
    """
    Clear all logs on device.

    WARNING: This action is destructive. All logs on the device will be permanently deleted and
    cannot be recovered.
    """
    raise NotImplementedError


def _check_log_dir(log_dir: Path, verbose: bool) -> None:
    """Check log directory parameters & exit CLI if issues are encountered."""
    try:
        flysight_type = classify_log_dir(log_dir)
    except ValueError:
        if verbose:
            print("Error: No log files found in provided log directory.")
        return

    if flysight_type == FlysightType.VERSION_1:
        if verbose:
            print("Error: Log trimming is currently not implemented for FlySight V1 hardware.")
        return


def _trim_pipeline(log_dir: Path, verbose: bool) -> None:
    if verbose:
        print(f"Trimming: {log_dir}...", end="")

    windowtrim_flight_log(log_dir, write_csv=True)

    if verbose:
        print("Done!")


@trim_app.command()
def single(
    log_dir: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    verbose: bool = typer.Option(True),
) -> None:
    """
    Trim single flight log.

    NOTE: Log trimming is currently only implemented for FlySight V2 hardware.
    """
    if log_dir is None:
        log_dir = prompt_for_dir(title="Select log directory for processing")

    _check_log_dir(log_dir, verbose=verbose)
    _trim_pipeline(log_dir, verbose=verbose)


@trim_app.command()
def batch(
    log_dir: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    verbose: bool = typer.Option(True),
) -> None:
    """
    Batch trim a directory of flight logs.

    NOTE: Log trimming is currently only implemented for FlySight V2 hardware.
    """
    if log_dir is None:
        log_dir = prompt_for_dir(title="Select directory for batch processing")

    for ld in iter_log_dirs(log_dir, flysight_type=FlysightType.VERSION_2):
        _check_log_dir(ld.log_dir, verbose=verbose)
        _trim_pipeline(ld.log_dir, verbose=verbose)


if __name__ == "__main__":  # pragma: no cover
    pyflysight_cli()
