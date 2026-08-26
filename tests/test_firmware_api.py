import pytest

from pyflysight.fw_api import APIResult, Device, FileObject, Firmware, Stack
from tests import SAMPLE_DATA_DIR

SAMPLE_API_RESPONSE_DIR = SAMPLE_DATA_DIR / "firmware_api"


def test_device_from_raw() -> None:
    SAMPLE_JSON = {
        "firmware_version": "v2024.12.30.8",
        "stack_version": "1.19.0",
        "stack_version_unknown": False,
        "pubkey_x": "abc123",
        "legacy": False,
    }
    TRUTH_DEVICE = Device(
        firmware_version="v2024.12.30.8",
        stack_version="1.19.0",
        stack_version_unknown=False,
        pubkey_x="abc123",
        legacy=False,
    )

    assert Device.from_raw(SAMPLE_JSON) == TRUTH_DEVICE


def test_file_object_from_raw() -> None:
    SAMPLE_JSON = {
        "url": "abc123",
        "target_path": "FW/APP.SFB",
        "size_bytes": 12345,
        "sha256": "def456",
    }
    TRUTH_FILE_OBJECT = FileObject(
        url="abc123", target_path="FW/APP.SFB", size_bytes=12345, sha256="def456"
    )

    assert FileObject.from_raw(SAMPLE_JSON) == TRUTH_FILE_OBJECT


def test_stack_no_update_from_raw() -> None:
    SAMPLE_JSON = {
        "required_version": "1.16.0",
        "current_version": "1.19.0",
        "current_version_unknown": False,
        "update_required": False,
        "file": None,
    }
    TRUTH_STACK = Stack(
        required_version="1.16.0",
        current_version="1.19.0",
        current_version_unknown=False,
        update_required=False,
        file=None,
    )

    assert Stack.from_raw(SAMPLE_JSON) == TRUTH_STACK


def test_stack_with_update_from_raw() -> None:
    SAMPLE_JSON = {
        "required_version": "1.19.0",
        "current_version": "1.16.0",
        "current_version_unknown": False,
        "update_required": True,
        "file": {
            "url": "abc123",
            "target_path": "FW/APP.SFB",
            "size_bytes": 12345,
            "sha256": "def456",
        },
    }
    TRUTH_STACK = Stack(
        required_version="1.19.0",
        current_version="1.16.0",
        current_version_unknown=False,
        update_required=True,
        file=FileObject(url="abc123", target_path="FW/APP.SFB", size_bytes=12345, sha256="def456"),
    )

    assert Stack.from_raw(SAMPLE_JSON) == TRUTH_STACK


def test_stack_update_required_no_file_raises() -> None:
    SAMPLE_JSON = {
        "required_version": "1.19.0",
        "current_version": "1.16.0",
        "current_version_unknown": False,
        "update_required": True,
        "file": None,
    }

    with pytest.raises(ValueError, match="Invalid manifest"):
        Stack.from_raw(SAMPLE_JSON)


def test_firmware_from_raw() -> None:
    SAMPLE_JSON = {
        "version": "v2024.12.30.10",
        "release_date": "2026-05-13",
        "is_beta": False,
        "release_notes_url": "abc123",
        "firmware": {
            "url": "def456",
            "target_path": "FW/APP.SFB",
            "size_bytes": 12345,
            "sha256": "ghi789",
        },
        "stack": {
            "required_version": "1.16.0",
            "current_version": "1.19.0",
            "current_version_unknown": False,
            "update_required": False,
            "file": None,
        },
    }
    TRUTH_FIRMWARE = Firmware(
        version="v2024.12.30.10",
        release_date="2026-05-13",
        is_beta=False,
        release_notes_url="abc123",
        firmware=FileObject(
            url="def456",
            target_path="FW/APP.SFB",
            size_bytes=12345,
            sha256="ghi789",
        ),
        stack=Stack(
            required_version="1.16.0",
            current_version="1.19.0",
            current_version_unknown=False,
            update_required=False,
            file=None,
        ),
    )

    assert Firmware.from_raw(SAMPLE_JSON) == TRUTH_FIRMWARE


def test_api_result_from_raw() -> None:
    SAMPLE_JSON = {
        "device": {
            "firmware_version": "v2024.12.30.8",
            "stack_version": "1.19.0",
            "stack_version_unknown": False,
            "pubkey_x": "abc123",
            "legacy": False,
        },
        "include_beta": False,
        "recommended": {
            "version": "v2024.12.30.10",
            "release_date": "2026-05-13",
            "is_beta": False,
            "release_notes_url": "def456",
            "firmware": {
                "url": "ghi789",
                "target_path": "FW/APP.SFB",
                "size_bytes": 12345,
                "sha256": "jkl123",
            },
            "stack": {
                "required_version": "1.19.0",
                "current_version": "1.19.0",
                "current_version_unknown": False,
                "update_required": False,
                "file": None,
            },
        },
        "firmwares": [
            {
                "version": "v2024.12.30.10",
                "release_date": "2026-05-13",
                "is_beta": False,
                "release_notes_url": "def456",
                "firmware": {
                    "url": "ghi789",
                    "target_path": "FW/APP.SFB",
                    "size_bytes": 12345,
                    "sha256": "jkl123",
                },
                "stack": {
                    "required_version": "1.19.0",
                    "current_version": "1.19.0",
                    "current_version_unknown": False,
                    "update_required": False,
                    "file": None,
                },
            },
            {
                "version": "v2024.12.30.8",
                "release_date": "2026-03-06",
                "is_beta": False,
                "release_notes_url": "mno456",
                "firmware": {
                    "url": "pqr789",
                    "target_path": "FW/APP.SFB",
                    "size_bytes": 67890,
                    "sha256": "stu123",
                },
                "stack": {
                    "required_version": "1.19.0",
                    "current_version": "1.19.0",
                    "current_version_unknown": False,
                    "update_required": False,
                    "file": None,
                },
            },
        ],
    }
    TRUTH_API_RESULT = APIResult(
        device=Device(
            firmware_version="v2024.12.30.8",
            stack_version="1.19.0",
            stack_version_unknown=False,
            pubkey_x="abc123",
            legacy=False,
        ),
        include_beta=False,
        recommended=Firmware(
            version="v2024.12.30.10",
            release_date="2026-05-13",
            is_beta=False,
            release_notes_url="def456",
            firmware=FileObject(
                url="ghi789",
                target_path="FW/APP.SFB",
                size_bytes=12345,
                sha256="jkl123",
            ),
            stack=Stack(
                required_version="1.19.0",
                current_version="1.19.0",
                current_version_unknown=False,
                update_required=False,
                file=None,
            ),
        ),
        firmwares=[
            Firmware(
                version="v2024.12.30.10",
                release_date="2026-05-13",
                is_beta=False,
                release_notes_url="def456",
                firmware=FileObject(
                    url="ghi789",
                    target_path="FW/APP.SFB",
                    size_bytes=12345,
                    sha256="jkl123",
                ),
                stack=Stack(
                    required_version="1.19.0",
                    current_version="1.19.0",
                    current_version_unknown=False,
                    update_required=False,
                    file=None,
                ),
            ),
            Firmware(
                version="v2024.12.30.8",
                release_date="2026-03-06",
                is_beta=False,
                release_notes_url="mno456",
                firmware=FileObject(
                    url="pqr789",
                    target_path="FW/APP.SFB",
                    size_bytes=67890,
                    sha256="stu123",
                ),
                stack=Stack(
                    required_version="1.19.0",
                    current_version="1.19.0",
                    current_version_unknown=False,
                    update_required=False,
                    file=None,
                ),
            ),
        ],
    )

    assert APIResult.from_raw(SAMPLE_JSON) == TRUTH_API_RESULT
