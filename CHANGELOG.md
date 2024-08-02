# Changelog
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`<major>`.`<minor>`.`<patch>`)

## [v0.4.0]
### Added
* Add derived `total_accel` column to Flysight V2 IMU sensor dataframe, calculated as a vector sum of the `xyz` acceleration components
* Add `pyflysight.log_utils.locate_log_subdir` helper for resolving child log directory from a given top-level directory
* Add `pyflysight.log_utils.iter_log_dirs` helper for iterating through child log directories of a given top-level directory
* #19 Add `pyflysight.config_utils` for config file generation
* #19 Add `pyflysight.flysight_utils` with helper utilities for working with connected FlySight devices

## [v0.3.0]
### Changed
* (Internal) Bump to Polars v1.x

### Added
* #18 Add `pyflysight.log_utils.classify_log_dir` helper for classifying the Flysight hardware rev of a given log directory

## [v0.2.0]
### Added
* Add parsing pipelines for Flysight V1 track data files
* #8 Add parsing pipelines for Flysight V2 track & sensor data files
* #11 Add trimming for Flysight V1 & V2 data files
* #12 Add simplified CSV log export for Flysight V2 data files

## [v0.1.0]
Initial release - yay!
