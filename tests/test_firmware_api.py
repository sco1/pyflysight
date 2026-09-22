import hashlib
import importlib
import json
import sys
import typing as t
from pathlib import Path

import niquests
import pytest
from pytest_mock import MockerFixture

import pyflysight
from pyflysight.fw_api import (
    APIResult,
    API_URL,
    Device,
    DownloadResult,
    FileObject,
    Firmware,
    Stack,
    _check_sha256,
    fetch_available_firmware,
)
from tests import SAMPLE_DATA_DIR

SAMPLE_API_RESPONSE_DIR = SAMPLE_DATA_DIR / "firmware_api"


@pytest.mark.parametrize("missing_module", ("anyio", "niquests"))
def test_missing_dep_raises(missing_module: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, missing_module, None)

    with pytest.raises(RuntimeError, match="fw_api"):
        importlib.reload(pyflysight.fw_api)


def test_check_file_sha(tmp_path: Path) -> None:
    test_file = tmp_path / "some_file"
    test_file.touch()
    other_test_file = tmp_path / "some_other_file"
    other_test_file.write_text("Viva Taco Bell")

    with test_file.open("rb") as f:
        TRUTH_HASH = hashlib.file_digest(f, "sha256").hexdigest()

    assert _check_sha256(target=test_file, expected_256_hash=TRUTH_HASH)
    assert not _check_sha256(target=other_test_file, expected_256_hash=TRUTH_HASH)


def test_check_file_sha_non_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="file"):
        _check_sha256(target=tmp_path, expected_256_hash="abc123")


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


def test_file_object_download(tmp_path: Path, mocker: MockerFixture) -> None:
    file_content = b"pretend firmware payload"
    file_obj = FileObject(
        url="https://example.com/fw.sfb",
        target_path="FW/APP.SFB",
        size_bytes=len(file_content),
        sha256=hashlib.sha256(file_content).hexdigest(),
    )

    mock_response = mocker.MagicMock()
    mock_response.iter_content.return_value = [file_content]
    mock_session = mocker.MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.Session")
    mock_session_cls.return_value.__enter__.return_value = mock_session

    out_path = file_obj.download(dest_dir=tmp_path)

    assert out_path == tmp_path / "FW" / "APP.SFB"
    assert out_path.read_bytes() == file_content
    mock_session.get.assert_called_once_with(file_obj.url, stream=True)


def test_file_object_download_overwrites_existing(tmp_path: Path, mocker: MockerFixture) -> None:
    file_content = b"new payload"
    file_obj = FileObject(
        url="https://example.com/fw.sfb",
        target_path="FW/APP.SFB",
        size_bytes=len(file_content),
        sha256=hashlib.sha256(file_content).hexdigest(),
    )

    existing = tmp_path / "FW" / "APP.SFB"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"stale payload, longer than the new one")

    mock_response = mocker.MagicMock()
    mock_response.iter_content.return_value = [file_content]
    mock_session = mocker.MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.Session")
    mock_session_cls.return_value.__enter__.return_value = mock_session

    out_path = file_obj.download(dest_dir=tmp_path)

    assert out_path.read_bytes() == file_content


def test_file_object_download_sha_mismatch_raises(tmp_path: Path, mocker: MockerFixture) -> None:
    file_obj = FileObject(
        url="https://example.com/fw.sfb",
        target_path="FW/APP.SFB",
        size_bytes=5,
        sha256="not_the_real_hash",
    )

    mock_response = mocker.MagicMock()
    mock_response.iter_content.return_value = [b"abcde"]
    mock_session = mocker.MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.Session")
    mock_session_cls.return_value.__enter__.return_value = mock_session

    with pytest.raises(RuntimeError, match="SHA256 Mismatch"):
        file_obj.download(dest_dir=tmp_path)


def test_file_object_download_skip_sha_check(tmp_path: Path, mocker: MockerFixture) -> None:
    file_obj = FileObject(
        url="https://example.com/fw.sfb",
        target_path="FW/APP.SFB",
        size_bytes=5,
        sha256="not_the_real_hash",
    )

    mock_response = mocker.MagicMock()
    mock_response.iter_content.return_value = [b"abcde"]
    mock_session = mocker.MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.Session")
    mock_session_cls.return_value.__enter__.return_value = mock_session

    out_path = file_obj.download(dest_dir=tmp_path, check_sha=False)

    assert out_path.read_bytes() == b"abcde"


@pytest.mark.asyncio
async def test_file_object_adownload(tmp_path: Path, mocker: MockerFixture) -> None:
    file_content = b"pretend async firmware payload"
    file_obj = FileObject(
        url="https://example.com/fw.sfb",
        target_path="FW/APP.SFB",
        size_bytes=len(file_content),
        sha256=hashlib.sha256(file_content).hexdigest(),
    )

    async def _chunks() -> t.AsyncIterator[bytes]:
        yield file_content

    mock_response = mocker.MagicMock()
    mock_response.iter_raw = mocker.AsyncMock(return_value=_chunks())
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.AsyncMock(return_value=mock_response)
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.AsyncSession")
    mock_session_cls.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session_cls.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    out_path = await file_obj.adownload(dest_dir=tmp_path)

    assert out_path == tmp_path / "FW" / "APP.SFB"
    assert out_path.read_bytes() == file_content
    mock_session.get.assert_awaited_once_with(file_obj.url, stream=True)


@pytest.mark.asyncio
async def test_file_object_adownload_sha_mismatch_raises(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    file_obj = FileObject(
        url="https://example.com/fw.sfb",
        target_path="FW/APP.SFB",
        size_bytes=5,
        sha256="not_the_real_hash",
    )

    async def _chunks() -> t.AsyncIterator[bytes]:
        yield b"abcde"

    mock_response = mocker.MagicMock()
    mock_response.iter_raw = mocker.AsyncMock(return_value=_chunks())
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.AsyncMock(return_value=mock_response)
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.AsyncSession")
    mock_session_cls.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session_cls.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    with pytest.raises(RuntimeError, match="SHA256 Mismatch"):
        await file_obj.adownload(dest_dir=tmp_path)


@pytest.mark.asyncio
async def test_file_object_adownload_skip_sha_check(tmp_path: Path, mocker: MockerFixture) -> None:
    file_obj = FileObject(
        url="https://example.com/fw.sfb",
        target_path="FW/APP.SFB",
        size_bytes=5,
        sha256="not_the_real_hash",
    )

    async def _chunks() -> t.AsyncIterator[bytes]:
        yield b"abcde"

    mock_response = mocker.MagicMock()
    mock_response.iter_raw = mocker.AsyncMock(return_value=_chunks())
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.AsyncMock(return_value=mock_response)
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.AsyncSession")
    mock_session_cls.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session_cls.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    out_path = await file_obj.adownload(dest_dir=tmp_path, check_sha=False)

    assert out_path.read_bytes() == b"abcde"


def test_stack_dl_prefix() -> None:
    stack = Stack(
        required_version="1.19.0",
        current_version="1.16.0",
        current_version_unknown=False,
        update_required=False,
        file=None,
    )

    assert stack._dl_prefix == "stack_1_19_0"


def test_stack_download_no_update_returns_none(tmp_path: Path) -> None:
    stack = Stack(
        required_version="1.19.0",
        current_version="1.19.0",
        current_version_unknown=False,
        update_required=False,
        file=None,
    )

    assert stack.download(dest_dir=tmp_path) is None


@pytest.mark.asyncio
async def test_stack_adownload_no_update_returns_none(tmp_path: Path) -> None:
    stack = Stack(
        required_version="1.19.0",
        current_version="1.19.0",
        current_version_unknown=False,
        update_required=False,
        file=None,
    )

    assert await stack.adownload(dest_dir=tmp_path) is None


def test_stack_download_with_update_delegates_to_file(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    file_obj = FileObject(url="abc123", target_path="FW/APP.SFB", size_bytes=1, sha256="def456")
    stack = Stack(
        required_version="1.19.0",
        current_version="1.16.0",
        current_version_unknown=False,
        update_required=True,
        file=file_obj,
    )

    mock_download = mocker.patch.object(FileObject, "download", return_value=Path("dummy_path"))

    result = stack.download(dest_dir=tmp_path, check_sha=False)

    assert result == Path("dummy_path")
    mock_download.assert_called_once_with(dest_dir=tmp_path / "stack_1_19_0", check_sha=False)


@pytest.mark.asyncio
async def test_stack_adownload_with_update_delegates_to_file(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    file_obj = FileObject(url="abc123", target_path="FW/APP.SFB", size_bytes=1, sha256="def456")
    stack = Stack(
        required_version="1.19.0",
        current_version="1.16.0",
        current_version_unknown=False,
        update_required=True,
        file=file_obj,
    )

    mock_adownload = mocker.patch.object(
        FileObject, "adownload", new=mocker.AsyncMock(return_value=Path("dummy_path"))
    )

    result = await stack.adownload(dest_dir=tmp_path, check_sha=False)

    assert result == Path("dummy_path")
    mock_adownload.assert_awaited_once_with(dest_dir=tmp_path / "stack_1_19_0", check_sha=False)


def test_firmware_fw_dl_prefix() -> None:
    firmware = Firmware(
        version="v2024.12.30.10",
        release_date="2026-05-13",
        is_beta=False,
        release_notes_url=None,
        firmware=FileObject(url="a", target_path="FW/APP.SFB", size_bytes=1, sha256="b"),
        stack=Stack(
            required_version="1.19.0",
            current_version="1.19.0",
            current_version_unknown=False,
            update_required=False,
            file=None,
        ),
    )

    assert firmware._fw_dl_prefix == "fw_v2024_12_30_10"


def test_firmware_download_delegates_to_components(tmp_path: Path, mocker: MockerFixture) -> None:
    firmware = Firmware(
        version="v2024.12.30.10",
        release_date="2026-05-13",
        is_beta=False,
        release_notes_url=None,
        firmware=FileObject(url="a", target_path="FW/APP.SFB", size_bytes=1, sha256="b"),
        stack=Stack(
            required_version="1.19.0",
            current_version="1.16.0",
            current_version_unknown=False,
            update_required=True,
            file=FileObject(url="c", target_path="FW/APP.SFB", size_bytes=1, sha256="d"),
        ),
    )

    mock_fw_download = mocker.patch.object(
        FileObject, "download", return_value=Path("fw_dummy_path")
    )
    mock_stack_download = mocker.patch.object(
        Stack, "download", return_value=Path("stack_dummy_path")
    )

    result = firmware.download(dest_dir=tmp_path, check_sha=False)

    assert result == DownloadResult(firmware=Path("fw_dummy_path"), stack=Path("stack_dummy_path"))
    mock_fw_download.assert_called_once_with(
        dest_dir=tmp_path / "fw_v2024_12_30_10", check_sha=False
    )
    mock_stack_download.assert_called_once_with(dest_dir=tmp_path, check_sha=False)


@pytest.mark.asyncio
async def test_firmware_adownload_delegates_to_components(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    firmware = Firmware(
        version="v2024.12.30.10",
        release_date="2026-05-13",
        is_beta=False,
        release_notes_url=None,
        firmware=FileObject(url="a", target_path="FW/APP.SFB", size_bytes=1, sha256="b"),
        stack=Stack(
            required_version="1.19.0",
            current_version="1.19.0",
            current_version_unknown=False,
            update_required=False,
            file=None,
        ),
    )

    mock_fw_adownload = mocker.patch.object(
        FileObject, "adownload", new=mocker.AsyncMock(return_value=Path("fw_dummy_path"))
    )
    mock_stack_adownload = mocker.patch.object(
        Stack, "adownload", new=mocker.AsyncMock(return_value=None)
    )

    result = await firmware.adownload(dest_dir=tmp_path, check_sha=False)

    assert result == DownloadResult(firmware=Path("fw_dummy_path"), stack=None)
    mock_fw_adownload.assert_awaited_once_with(
        dest_dir=tmp_path / "fw_v2024_12_30_10", check_sha=False
    )
    mock_stack_adownload.assert_awaited_once_with(dest_dir=tmp_path, check_sha=False)


def test_fetch_available_firmware(mocker: MockerFixture) -> None:
    sample_json = json.loads(
        (SAMPLE_API_RESPONSE_DIR / "sample_firmware_response_with_beta.json").read_text()
    )

    mock_response = mocker.MagicMock()
    mock_response.json.return_value = sample_json
    mock_session = mocker.MagicMock()
    mock_session.post.return_value = mock_response
    mock_session_cls = mocker.patch("pyflysight.fw_api.niquests.Session")
    mock_session_cls.return_value.__enter__.return_value = mock_session

    result = fetch_available_firmware(device_info="<FLYSIGHT.TXT contents>", include_beta=True)

    assert result == APIResult.from_raw(sample_json)
    mock_response.raise_for_status.assert_called_once()
    mock_session.post.assert_called_once_with(
        url=API_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps({"flysight_txt": "<FLYSIGHT.TXT contents>"}),
        params={"include_beta": "True"},
    )


def test_fetch_available_firmware_default_include_beta(mocker: MockerFixture) -> None:
    sample_json = json.loads(
        (SAMPLE_API_RESPONSE_DIR / "sample_firmware_response_with_beta.json").read_text()
    )

    mock_response = mocker.MagicMock()
    mock_response.json.return_value = sample_json
    mock_session = mocker.MagicMock()
    mock_session.post.return_value = mock_response
    mocker.patch("pyflysight.fw_api.niquests.Session").return_value.__enter__.return_value = (
        mock_session
    )

    fetch_available_firmware(device_info="<FLYSIGHT.TXT contents>")

    assert mock_session.post.call_args.kwargs["params"] == {"include_beta": "False"}


def test_fetch_available_firmware_propagates_http_error(mocker: MockerFixture) -> None:
    mock_response = mocker.MagicMock()
    mock_response.raise_for_status.side_effect = niquests.HTTPError("500 Server Error")
    mock_session = mocker.MagicMock()
    mock_session.post.return_value = mock_response
    mocker.patch("pyflysight.fw_api.niquests.Session").return_value.__enter__.return_value = (
        mock_session
    )

    with pytest.raises(niquests.HTTPError):
        fetch_available_firmware(device_info="<FLYSIGHT.TXT contents>")
