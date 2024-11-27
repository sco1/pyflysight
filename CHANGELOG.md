# Changelog
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`<major>`.`<minor>`.`<patch>`)

## [0.9.0]
### Changed
* #44 Add optional consideration for the `./TEMP` log directory on FlySight V2 hardware. This directory contains log sessions that have not yet been finalized and may contain the entire flight log of interest in certain situations (e.g. battery has depleted)

### Fixed
* #45 Enhance error message for mismatched series dimensions when parsing raw log files. This is typically encountered when the device is interrupted while finalizing log data and does not finish writing out one or more data rows

## [0.8.0]
### Added
* #35 Add a `prefer_processed` kwarg to the `pyflysight.flysight_proc.parse_v2_log_directory` helper pipeline to prefer loading a serialized `pyflysight.flysight_proc.FlysightV2FlightLog` instance, if detected, rather than parsing the raw data files

### Changed
* (Internal) Move some commonly used/caught exceptions to `pyflysight.exceptions` for more granular exception handling
* #41 `pyflysight log_convert single` and `pyflysight trim single` are now more tolerant of directory specification when provided a top-level directory containing only one child logging session; the child directory should now automatically be resolved prior to processing

## [0.7.0]
### Added
* #15 Add `pyflysight.flysight_proc.FlysightV1` and `pyflysight.flysight_proc.FlysightV1FlightLog` container classes for interfacing with FlySight V1 track data & metadata
* #30 Add optional normalization of GPS coordinates in plaintext log files
* #34 Add CLI pipeline for parsing FlySight V2 flight logs into more user-friendly CSV files.

### Changed
* (Internal) #21 Utilize MkDocs for documentation generation
* #15 FlySight V1 related parsing helpers now utilize `pyflysight.flysight_proc.FlysightV1FlightLog` instances rather than bare `DataFrame`s
* (Internal) Migrate to uv from poetry

## [0.6.0]
### Added
* #24 Add optional normalization of parsed GPS coordinates
* #27 Add `filter_accel` and `filter_baro` helpers to `pyflysight.flysight_proc.FlysightV2FlightLog` to assist with applying filters to logged accelerometer & baro data.
* #26 Add `pyflysight.flysight_proc.calculate_sync_delta` for calculating the time delta required to align the parsed track & sensor data

### Changed
* #26 When using `pyflysight.flysight_proc.parse_v2_log_directory`, an `elapsed_time_sensor` column is now added to the track `DataFrame`, providing a synchronized elapsed time that can be used to align the sensor & track `DataFrame`s

### Fixed
* #25 Re-initialize nested configuration dataclasses when loading from JSON

## [0.5.1]
### Added
* Add `py.typed` marker to register library as typed for downstream type checking

## [0.5.0]
### Changed
* #16 Complete reimplementation of CLI

### Added
* Add additional helpers to `pyflysight.config_utils` and `pyflysight.flysight_utils`
* (Internal) #21 Add documentation autogeneration using `pdoc3`

## [v0.4.0]
### Added
* Add derived `total_accel` column to FlySight V2 IMU sensor dataframe, calculated as a vector sum of the `xyz` acceleration components
* Add `pyflysight.log_utils.locate_log_subdir` helper for resolving child log directory from a given top-level directory
* Add `pyflysight.log_utils.iter_log_dirs` helper for iterating through child log directories of a given top-level directory
* #19 Add `pyflysight.config_utils` for config file generation
* #19 Add `pyflysight.flysight_utils` with helper utilities for working with connected FlySight devices

## [v0.3.0]
### Changed
* (Internal) Bump to Polars v1.x

### Added
* #18 Add `pyflysight.log_utils.classify_log_dir` helper for classifying the FlySight hardware rev of a given log directory

## [v0.2.0]
### Added
* Add parsing pipelines for FlySight V1 track data files
* #8 Add parsing pipelines for FlySight V2 track & sensor data files
* #11 Add trimming for FlySight V1 & V2 data files
* #12 Add simplified CSV log export for FlySight V2 data files

## [v0.1.0]
Initial release - yay!
