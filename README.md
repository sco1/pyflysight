# PyFlySight
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyflysight/0.1.0?logo=python&logoColor=FFD43B)](https://pypi.org/project/pyflysight/)
[![PyPI](https://img.shields.io/pypi/v/pyflysight?logo=Python&logoColor=FFD43B)](https://pypi.org/project/pyflysight/)
[![PyPI - License](https://img.shields.io/pypi/l/pyflysight?color=magenta)](https://github.com/sco1/pyflysight/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/pyflysight/main.svg)](https://results.pre-commit.ci/latest/github/sco1/pyflysight/main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)

Helper library for processing [FlySight GPS](https://www.flysight.ca/) flight logs.

🚨 This is an alpha project. User-facing functionality is still under development 🚨

## Installation
Install from PyPi with your favorite `pip` invocation:

```bash
$ pip install pyflysight
```

You can confirm proper installation via the `pyflysight` CLI:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["pyflysight", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"```bash\n$ pyflysight --help\n{out.stdout.rstrip()}\n```"
)
]]] -->
```bash
$ pyflysight --help
Usage: pyflysight [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  batch   Batch flight log processing pipeline.
  single  Single flight log processing pipeline.
```
<!-- [[[end]]] -->

## Usage
### Environment Variables
The following environment variables are provided to help customize pipeline behaviors.

| Variable Name      | Description                       | Default      |
|--------------------|-----------------------------------|--------------|
| `PROMPT_START_DIR` | Start path for UI file/dir prompt | `'.'`        |

### `pyflysight single`
Process a single FlySight log file.
#### Input Parameters
| Parameter              | Description                    | Type         | Default    |
|------------------------|--------------------------------|--------------|------------|
| `--log-filepath`       | Path to FlySight log to parse. | `Path\|None` | GUI Prompt |

### `pyflysight batch`
Batch process a directory of FlySight log files.
#### Input Parameters
| Parameter              | Description                                   | Type         | Default    |
|------------------------|-----------------------------------------------|--------------|------------|
| `--log-dir`            | Path to FlySight log directory to parse.      | `Path\|None` | GUI Prompt |
| `--log-pattern`        | FlySight log file glob pattern.<sup>1,2</sup> | `str`        | `"*.CSV"`  |

1. Case sensitivity is deferred to the host OS
2. Recursive globbing requires manual specification (e.g. `**/*.CSV`)

## Contributing
### Development Environment
This project uses [Poetry](https://python-poetry.org/) to manage dependencies. With your fork cloned to your local machine, you can install the project and its dependencies to create a development environment using:

```bash
$ poetry install
```

A [pre-commit](https://pre-commit.com) configuration is also provided to create a pre-commit hook so linting errors aren't committed:

```bash
$ pre-commit install
```

### Testing & Coverage
A [pytest](https://docs.pytest.org/en/latest/) suite is provided, with coverage reporting from [pytest-cov](https://github.com/pytest-dev/pytest-cov). A [tox](https://github.com/tox-dev/tox/) configuration is provided to test across all supported versions of Python. Testing will be skipped for Python versions that cannot be found.

```bash
$ tox
```

Details on missing coverage, including in the test suite, is provided in the report to allow the user to generate additional tests for full coverage.
