import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from sco1_misc.prompts import prompt_for_dir, prompt_for_file

pyflysight_cli = typer.Typer(add_completion=False)

load_dotenv()
PROMPT_START_DIR = Path(os.environ.get("PROMPT_START_DIR", "."))


@pyflysight_cli.command()
def single(
    log_filepath: Path = typer.Option(None, exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Single flight log processing pipeline."""
    if log_filepath is None:
        log_filepath = prompt_for_file(
            title="Select Flight Log",
            start_dir=PROMPT_START_DIR,
            filetypes=[
                ("FlySight Flight Log", "*.csv"),
                ("All Files", "*.*"),
            ],
        )

    raise NotImplementedError


@pyflysight_cli.command()
def batch(
    log_dir: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    log_pattern: str = typer.Option("*.CSV"),
    verbose: bool = typer.Option(True),
) -> None:
    """Batch flight log processing pipeline."""
    if log_dir is None:
        log_dir = prompt_for_dir(
            title="Select directory for batch processing", start_dir=PROMPT_START_DIR
        )

    raise NotImplementedError


if __name__ == "__main__":  # pragma: no cover
    pyflysight_cli()
