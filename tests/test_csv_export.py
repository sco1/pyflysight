from pathlib import Path

from pyflysight.flysight_proc import parse_v2_log_directory

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"
SAMPLE_LOG = SAMPLE_DATA_DIR / "24-04-20/04-20-00"


def test_simplified_csv_export(tmp_path: Path) -> None:
    # Since this relies mostly on polars' DataFrame.write_csv, we don't need to test that
    # functionality again. Instead, just test that the correct directories & file(s) are created
    flight_log = parse_v2_log_directory(SAMPLE_LOG)
    flight_log.to_csv(tmp_path)

    truth_output_dir = tmp_path / "003e0038484e501420353131/3e10c2f6b1ea4604758b8926"
    assert truth_output_dir.exists()

    truth_sensor_files = {"IMU.CSV", "TRACK.CSV"}
    out_filenames = {file.name for file in truth_output_dir.glob("*.CSV")}
    assert out_filenames == truth_sensor_files
