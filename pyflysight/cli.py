from pathlib import Path

import typer
from sco1_misc.prompts import prompt_for_dir, prompt_for_file

pyflysight_cli = typer.Typer(add_completion=False)


@pyflysight_cli.command()
def single(
    log_filepath: Path = typer.Option(None, exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Single flight log processing pipeline."""
    raise NotImplementedError

    if log_filepath is None:
        log_filepath = prompt_for_file(
            title="Select Flight Log",
            filetypes=[
                ("FlySight Flight Log", "*.csv"),
                ("All Files", "*.*"),
            ],
        )


@pyflysight_cli.command()
def batch(
    log_dir: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    log_pattern: str = typer.Option("*.CSV"),
    verbose: bool = typer.Option(True),
) -> None:
    """Batch flight log processing pipeline."""
    raise NotImplementedError

    if log_dir is None:
        log_dir = prompt_for_dir(title="Select directory for batch processing")


if __name__ == "__main__":  # pragma: no cover
    pyflysight_cli()
