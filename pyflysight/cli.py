import shutil
import typing as t
from pathlib import Path

import typer
from sco1_misc.prompts import prompt_for_dir, prompt_for_file

from pyflysight import FlysightType
from pyflysight.config_utils import FlysightConfig, FlysightV1Config, FlysightV2Config
from pyflysight.flysight_utils import (
    classify_hardware_type,
    copy_logs,
    erase_logs,
    get_device_metadata,
    get_flysight_drives,
    wait_for_flysight,
    write_config,
)
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


def _abort_with_message(message: str, end: str = "") -> t.Never:
    print(message, end=end)
    raise typer.Abort() from None


def _print_connected_drives(flysight_drives: t.Iterable[Path]) -> None:
    for idx, drive in enumerate(flysight_drives):
        md = get_device_metadata(drive)
        md_str = (
            f"{idx}. {drive} - FlySight V{md.flysight_type}, Logs Available: {md.n_logs}\n"
            f"    Serial: {md.serial}\n"
            f"    Firmware: {md.firmware}"
        )
        print(md_str)


def _ask_select_flysight() -> Path:
    """List connected FlySight drives and prompt user for selection."""
    flysight_drives = get_flysight_drives()
    if not flysight_drives:
        raise RuntimeError("No connected FlySight drives detected.")

    _print_connected_drives(flysight_drives)
    select = typer.prompt(
        "Please select a connected FlySight (-1 to abort)", default=0, type=int, show_default=False
    )
    if select < 0:
        raise typer.Abort()

    try:
        return flysight_drives[select]
    except IndexError:
        _abort_with_message("Error: Invalid drive selection. ")


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


def _try_write_config(device_root: Path, config: FlysightConfig, backup_existing: bool) -> None:
    """Wrap config writing utility with graceful handling for errors."""
    print(f"Writing config to: {device_root}")
    try:
        write_config(device_root=device_root, config=config, backup_existing=backup_existing)
        print(f"Config successfully written to: {device_root}")
    except PermissionError:
        _abort_with_message("Error: FlySight device is read-only. ")


@config_app.command()
def write_default(
    flysight_root: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    backup_existing: bool = typer.Option(True),
) -> None:
    """
    Write default configuration.

    WARNING: This action is destructive. All existing configuration information & formatting will be
    permanently lost.
    """
    if flysight_root is None:
        flysight_root = _ask_select_flysight()

    flysight_type = classify_hardware_type(flysight_root)
    config: FlysightConfig
    if flysight_type == FlysightType.VERSION_1:
        config = FlysightV1Config()
    elif flysight_type == FlysightType.VERSION_2:
        config = FlysightV2Config()

    _try_write_config(device_root=flysight_root, config=config, backup_existing=backup_existing)


@config_app.command()
def write_from_json(
    flysight_root: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    config_source: Path = typer.Option(None, exists=True, file_okay=True, dir_okay=False),
    backup_existing: bool = typer.Option(True),
) -> None:
    """
    Write previously serialized paramters.

    WARNING: This action is destructive. All existing configuration information & formatting will be
    permanently lost.
    """
    if flysight_root is None:
        flysight_root = _ask_select_flysight()

    if config_source is None:
        config_source = prompt_for_file(
            title="Select serialized configuration to copy",
            filetypes=[
                ("Serialized FlySight Configuration", "*.json"),
                ("All Files", "*.*"),
            ],
        )

    flysight_type = classify_hardware_type(flysight_root)
    config: FlysightConfig
    if flysight_type == FlysightType.VERSION_1:
        config = FlysightV1Config.from_json(config_source)
    elif flysight_type == FlysightType.VERSION_2:
        config = FlysightV2Config.from_json(config_source)

    _try_write_config(device_root=flysight_root, config=config, backup_existing=backup_existing)


@config_app.command()
def write_from_other(
    flysight_root: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    config_source: Path = typer.Option(None, exists=True, file_okay=True, dir_okay=False),
    backup_existing: bool = typer.Option(True),
) -> None:
    """
    Copy configuration from file.

    WARNING: This action is destructive. All existing configuration information & formatting will be
    permanently lost.
    """
    if flysight_root is None:
        flysight_root = _ask_select_flysight()

    if config_source is None:
        config_source = prompt_for_file(
            title="Select configuration to copy",
            filetypes=[
                ("FlySight Configuration", "CONFIG.TXT"),
                ("All Files", "*.*"),
            ],
        )

    flysight_config_filepath = flysight_root / "CONFIG.TXT"
    try:
        if flysight_config_filepath.exists() and backup_existing:
            backup_filepath = flysight_root / "CONFIG_OLD.TXT"
            shutil.copy(flysight_config_filepath, backup_filepath)

        shutil.copy(config_source, flysight_config_filepath)
    except PermissionError:
        _abort_with_message("Error: FlySight device is read-only. ")


@log_app.command()
def copy(
    flysight_root: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    dest: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    exist_ok: bool = typer.Option(True),
) -> None:
    """Copy all logs on device to the specified destination."""
    if flysight_root is None:
        flysight_root = _ask_select_flysight()

    drive_metadata = get_device_metadata(flysight_root)
    if drive_metadata.n_logs == 0:
        print("No logs on device to copy.")
        return

    if dest is None:
        dest = prompt_for_dir(title="Select Log Destination")

    copy_status = copy_logs(
        device_root=flysight_root, dest=dest, exist_ok=exist_ok, remove_after=False
    )
    print(f"Copied {copy_status.n_dirs_copied} log directories to {dest}")


@log_app.command()
def clear(
    flysight_root: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    force: bool = typer.Option(False),
) -> None:
    """
    Clear all logs on device.

    WARNING: This action is destructive. All logs on the device will be permanently deleted and
    cannot be recovered.
    """
    if flysight_root is None:
        flysight_root = _ask_select_flysight()

    drive_metadata = get_device_metadata(flysight_root)
    if drive_metadata.n_logs == 0:
        print("No logs on device to erase.")
        return

    if not force:
        confirm_clear = typer.confirm(f"This will erase {drive_metadata.n_logs} logs. Confirm?")
        if not confirm_clear:
            raise typer.Abort()

    try:
        erase_logs(flysight_root)
    except PermissionError:
        _abort_with_message("Error: FlySight device is write protected. ")


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
        log_dir = prompt_for_dir(title="Select Log Directory For Processing")

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
        log_dir = prompt_for_dir(title="Select Directory For Batch Processing")

    for ld in iter_log_dirs(log_dir, flysight_type=FlysightType.VERSION_2):
        _check_log_dir(ld.log_dir, verbose=verbose)
        _trim_pipeline(ld.log_dir, verbose=verbose)


if __name__ == "__main__":  # pragma: no cover
    pyflysight_cli()
