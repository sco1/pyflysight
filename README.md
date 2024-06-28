# pyflysight
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyflysight/0.2.0?logo=python&logoColor=FFD43B)](https://pypi.org/project/pyflysight/)
[![PyPI](https://img.shields.io/pypi/v/pyflysight?logo=Python&logoColor=FFD43B)](https://pypi.org/project/pyflysight/)
[![PyPI - License](https://img.shields.io/pypi/l/pyflysight?color=magenta)](https://github.com/sco1/pyflysight/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/pyflysight/main.svg)](https://results.pre-commit.ci/latest/github/sco1/pyflysight/main)

Helper library for processing [FlySight GPS](https://www.flysight.ca/) flight logs. Support is provided for both the V1 and V2 hardware revisions, see: [Hardware Revisions](#hardware-revisions) for a description of the differences between the two.

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

## CLI Usage
🚨 **NOTE:** CLI functionality is currently still under development. 🚨

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

## Internal Data Representation
See: [Data Format](/doc/data_format.md) for a more detailed breakdown of the expected data file formats.

`pyflysight` exposes helpers for parsing your flight data from their CSV representation into a [Polars](https://docs.pola.rs/) dataframe. All dataframes derive an `elapsed_time` column, calculated as the delta of the row timestamp from the first seen timestamp of the data file. All GPS dataframes calculate a `groundspeed` column from the northing and easting GPS velocity components.

### Flysight V1
`pyflysight.flysight_proc.load_flysight` parses the GPS track log into a dataframe, inferring column names from the first row of the CSV; unit information is discarded.

`pyflysight.flysight_proc.batch_load_flysight` wraps `pyflysight.flysight_proc.load_flysight` to batch load a directory of logs into a dictionary of dataframes. Because the FlySight V1 hardware groups logs by date & the log CSV name does not contain date information, the date is inferred from the log's parent directory name & the output dictionary is of the form `{log date: {log_time: DataFrame}}`.

### Flysight V2
Both the `SENSOR.CSV` and `TRACK.CSV` files share a similar data format: a series of header rows followed by a series of data rows. As the filenames suggest, `SENSOR.CSV` contains all of the onboard sensor information and `TRACK.CSV` contains the GPS track. `RAW.UBX` is the raw binary data stream from the onboard u-blox hardware; at this time this file is currently ignored.

`pyflysight.flysight_proc.parse_v2_log_directory` is intended to be the main user interface, which wraps the data parsing pipelines and outputs an instance of the `pyflysight.flysight_proc.FlysightV2FlightLog` container class.

## Interactive Log Trimming
🚨 **NOTE:** Log trimming is currently only implemented for Flysight V2 data. 🚨

`pyflysight.trim_app.windowtrim_flight_log` allows the user to interactively trim your Flysight log data using a plot of the elapsed time vs. pressure altitude. Trimmed data may be optionally written to disk into a directory of files, named by the current flight session. A CSV file is created for each sensor present, along with the GPS track and device information:

```
.
└── device/
    └── session/
        ├── BARO.CSV
        ├── device_info.json
        ├── IMU.CSV
        ├── TRACK.CSV
        └── ...
```

Data trimming & CSV export is handled programmatically by methods of `pyflysight.flysight_proc.FlysightV2FlightLog`. The CSV output is designed to be round-trippable.

## Hardware Revisions
![hardware comparison](/doc/hardware_revs.png)

Flysight released a new hardware revision in Summer 2023 with many improvements over the original, including the addition of additional sensors. In addition to the GPS information logged by the Flysight V1, the Flysight V2 adds IMU & environmental data streams to your flight logs. The main user-facing change is a difference in log output.

Where the Flysight V1 log output looks something like:

```
.
└── 24-04-20/
    └── 04-20-00.CSV
```

The Flysight V2 log output looks something like:

```
.
└── 24-04-20/
    └── 04-20-00/
        ├── RAW.UBX
        ├── SENSOR.CSV
        └── TRACK.CSV
```

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
