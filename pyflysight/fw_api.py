import functools
import hashlib
import json
import platform
import typing as t
from pathlib import Path

try:
    import anyio
    import niquests
except ImportError:
    raise RuntimeError("Please install the 'fw_api' dependency group") from None

from pyflysight import __url__, __version__

API_URL = "https://flysight.ca/wp-json/flysight/v1/firmware"

USER_AGENT = (
    f"pyflysight/{__version__} ({__url__}) "
    f"niquests/{niquests.__version__} "
    f"{platform.python_implementation()}/{platform.python_version()}"
)


def _check_sha256(target: Path, expected_256_hash: str) -> bool:
    """Check the SHA256 hash of the `target` file against the expected hash."""
    if not target.is_file():
        raise ValueError(f"Target must be a file: '{target}'")

    with target.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256")

    return digest.hexdigest() == expected_256_hash


class Device(t.NamedTuple):
    """Flysight device metadata, as reported by the firmware API."""

    firmware_version: str
    stack_version: str
    stack_version_unknown: bool  # True if stack version was missing or invalid in FLYSIGHT.TXT
    pubkey_x: str  # Used for compatibility matching
    legacy: bool  # API received an older FLYSIGHT.TXT format without pubkey_x

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        """
        Build a `Device` instance from the firmware API response.

        The following keys are expected to be present in the response:
            * `firmware_version`
            * `stack_version`
            * `stack_version_unknown`
            * `pubkey_x`
            * `legacy`

        Any other fields, if present, are ignored.
        """
        return cls(
            firmware_version=raw_json["firmware_version"],
            stack_version=raw_json["stack_version"],
            stack_version_unknown=raw_json["stack_version_unknown"],
            pubkey_x=raw_json["pubkey_x"],
            legacy=raw_json["legacy"],
        )


class FileObject(t.NamedTuple):
    """
    Flysight firmware API file object representation.

    Provides download information for a firmware or stack update file.
    """

    url: str
    target_path: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        """
        Build a `FileObject` instance from the firmware API response.

        The following keys are expected to be present in the response:
            * `url`
            * `target_path`
            * `size_bytes`
            * `sha256`

        Any other fields, if present, are ignored.
        """
        return cls(
            url=raw_json["url"],
            target_path=raw_json["target_path"],
            size_bytes=raw_json["size_bytes"],
            sha256=raw_json["sha256"],
        )

    def download(self, dest_dir: Path, check_sha: bool = True) -> Path:
        """
        Download the file object to the specified `dest_dir`, returning the downloaded file path.

        `dest_dir` is assumed to be a path to the desired root directory; the downloaded file will
        be saved according to the path defined by `self.target_path`, e.g. if `self.target_path` is
        `FW/APP.SFB`, the file will be downloaded to `dest_dir/FW/APP.SFB`.

        Warning:
            Any existing download at the derived filepath will be overwritten.

        If `check_sha` is `True`, the SHA256 hash of the downloaded file is compared to the expected
        hash provided by the firmware API; an exception is raised if the hashes do not match.
        """
        dl_filepath = dest_dir / self.target_path
        dl_filepath.parent.mkdir(parents=True, exist_ok=True)
        with niquests.Session(headers={"User-Agent": USER_AGENT}) as s:
            r = s.get(self.url, stream=True)
            with dl_filepath.open("wb") as f:
                for chunk in r.iter_content():
                    f.write(chunk)

        if check_sha and not _check_sha256(dl_filepath, self.sha256):
            raise RuntimeError("SHA256 Mismatch")

        return dl_filepath

    async def adownload(self, dest_dir: Path, check_sha: bool = True) -> Path:
        """
        Download the file object to the specified `dest_dir`, returning the downloaded file path.

        Note:
            This is an async method.

        `dest_dir` is assumed to be a path to the desired root directory; the downloaded file will
        be saved according to the path defined by `self.target_path`, e.g. if `self.target_path` is
        `FW/APP.SFB`, the file will be downloaded to `dest_dir/FW/APP.SFB`.

        Warning:
            Any existing download at the derived filepath will be overwritten.

        If `check_sha` is `True`, the SHA256 hash of the downloaded file is compared to the expected
        hash provided by the firmware API; an exception is raised if the hashes do not match.
        """
        dl_filepath = dest_dir / self.target_path
        dl_filepath.parent.mkdir(parents=True, exist_ok=True)

        async with niquests.AsyncSession(headers={"User-Agent": USER_AGENT}) as s:
            r = await s.get(self.url, stream=True)
            async with await anyio.open_file(dl_filepath, "wb") as f:
                async for chunk in await r.iter_raw():
                    await f.write(chunk)

        if not _check_sha256(dl_filepath, self.sha256):
            raise RuntimeError("SHA256 Mismatch")

        return dl_filepath


class Stack(t.NamedTuple):
    """Flysight stack metadata, as reported by the firmware API."""

    required_version: str
    current_version: str
    current_version_unknown: bool  # True if stack version was missing or invalid in FLYSIGHT.TXT
    update_required: bool
    file: FileObject | None  # None if no update is required

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        """
        Build a `Stack` instance from the firmware API response.

        The following keys are expected to be present in the response:
            * `required_version`
            * `current_version`
            * `current_version_unknown`
            * `update_required`
            * `file`

        Any other fields, if present, are ignored.

        Note:
            A validity check is performed on the API response prior to deserialization; if
            `update_required` is `True`, then `file` must not be `None`.
        """
        # Pull for manifest checking
        update_required = raw_json["update_required"]

        if raw_json["file"] is None:
            stack_file = None

            if update_required:
                raise ValueError("Invalid manifest: stack update required but file not provided")
        else:
            stack_file = FileObject.from_raw(raw_json["file"])

        return cls(
            required_version=raw_json["required_version"],
            current_version=raw_json["current_version"],
            current_version_unknown=raw_json["current_version_unknown"],
            update_required=update_required,
            file=stack_file,
        )

    @functools.cached_property
    def _dl_prefix(self) -> str:
        """Build a unique parent directory name based on `self.required_version`."""
        return f"stack_{self.required_version.replace('.', '_')}"

    def download(self, dest_dir: Path, check_sha: bool = True) -> Path | None:
        """
        Download the stack to the specified `dest_dir`.

        If a stack update is provided, the path to the downloaded file will be returned, otherwise
        `None`.

        `dest_dir` is assumed to be a path to the desired root directory; if available, the
        downloaded file will be saved according to the path defined by both the required version and
        `Stack`'s `file` metadata, e.g. if we have `required_version` `v1.0.0` and
        `file.target_path` is `FW/APP.SFB`, the file will be downloaded to:
        `dest_dir/stack_v1_0_0/FW/APP.SFB`.

        Warning:
            Any existing download at the derived filepath will be overwritten.

        If `check_sha` is `True`, the SHA256 hash of the downloaded file is compared to the expected
        hash provided by the firmware API; an exception is raised if the hashes do not match.
        """
        if self.file is None:
            return None

        dest_dir = dest_dir / self._dl_prefix
        return self.file.download(dest_dir=dest_dir, check_sha=check_sha)

    async def adownload(self, dest_dir: Path, check_sha: bool = True) -> Path | None:
        """
        Asynchronously download the stack to the specified `dest_dir`.

        If a stack update is provided, the path to the downloaded file will be returned, otherwise
        `None`.

        `dest_dir` is assumed to be a path to the desired root directory; if available, the
        downloaded file will be saved according to the path defined by both the required version and
        `Stack`'s `file` metadata, e.g. if we have `required_version` `v1.0.0` and
        `file.target_path` is `FW/APP.SFB`, the file will be downloaded to:
        `dest_dir/stack_v1_0_0/FW/APP.SFB`.

        Warning:
            Any existing download at the derived filepath will be overwritten.

        If `check_sha` is `True`, the SHA256 hash of the downloaded file is compared to the expected
        hash provided by the firmware API; an exception is raised if the hashes do not match.
        """
        if self.file is None:
            return None

        dest_dir = dest_dir / self._dl_prefix
        return await self.file.adownload(dest_dir=dest_dir, check_sha=check_sha)


class DownloadResult(t.NamedTuple):  # noqa: D101
    firmware: Path
    stack: Path | None


class Firmware(t.NamedTuple):
    """Flysight firmware metadata, as reported by the firmware API."""

    version: str
    release_date: str
    is_beta: bool
    release_notes_url: str | None
    firmware: FileObject
    stack: Stack

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        """
        Build a `Firmware` instance from the firmware API response.

        The following keys are expected to be present in the response:
            * `version`
            * `release_date`
            * `is_beta`
            * `release_notes_url`
            * `firmware`
            * `stack`

        Any other fields, if present, are ignored.

        Expected fields the `firmware` and `stack` subcomponents are detailed in the API
        documentation as well as their respective `from_raw` methods.
        """
        return cls(
            version=raw_json["version"],
            release_date=raw_json["release_date"],
            is_beta=raw_json["is_beta"],
            release_notes_url=raw_json["release_notes_url"],
            firmware=FileObject.from_raw(raw_json["firmware"]),
            stack=Stack.from_raw(raw_json["stack"]),
        )

    @functools.cached_property
    def _fw_dl_prefix(self) -> str:
        """Build a unique parent directory name based on `self.version`."""
        return f"fw_{self.version.replace('.', '_')}"

    def download(self, dest_dir: Path, check_sha: bool = True) -> DownloadResult:
        """
        Download the firmware file(s) to the specified `dest_dir`.

        Path(s) to the downloaded files are returned; if no stack update is required then `None`
        will instead be provided.

        `dest_dir` is assumed to be a path to the desired root directory. Firmware and, if present,
        stack updates will be downloaded to a child directory derived from their component metadata
        (version and target path). For example, if firmware and stack version `v1.0.0` are
        downloaded, their paths will be:
            * Firmware: `dest_dir/fw_v1_0_0/FW/APP.SFB`
            * Stack: `dest_dir/stack_v1_0_0/FW/APP.SFB`

        Warning:
            Any existing download at the derived filepath will be overwritten.

        If `check_sha` is `True`, the SHA256 hash of each downloaded file is compared to the
        expected hash provided by the firmware API; an exception is raised if the hashes do not
        match.
        """
        fw_dest_dir = dest_dir / self._fw_dl_prefix
        return DownloadResult(
            firmware=self.firmware.download(dest_dir=fw_dest_dir, check_sha=check_sha),
            stack=self.stack.download(dest_dir=dest_dir, check_sha=check_sha),
        )

    async def adownload(self, dest_dir: Path, check_sha: bool = True) -> DownloadResult:
        """
        Asynchronously download the firmware file(s) to the specified `dest_dir`.

        Path(s) to the downloaded files are returned; if no stack update is required then `None`
        will instead be provided.

        `dest_dir` is assumed to be a path to the desired root directory. Firmware and, if present,
        stack updates will be downloaded to a child directory derived from their component metadata
        (version and target path). For example, if firmware and stack version `v1.0.0` are
        downloaded, their paths will be:
            * Firmware: `dest_dir/fw_v1_0_0/FW/APP.SFB`
            * Stack: `dest_dir/stack_v1_0_0/FW/APP.SFB`

        Warning:
            Any existing download at the derived filepath will be overwritten.

        If `check_sha` is `True`, the SHA256 hash of each downloaded file is compared to the
        expected hash provided by the firmware API; an exception is raised if the hashes do not
        match.
        """
        fw_dest_dir = dest_dir / self._fw_dl_prefix
        return DownloadResult(
            firmware=await self.firmware.adownload(dest_dir=fw_dest_dir, check_sha=check_sha),
            stack=await self.stack.adownload(dest_dir=dest_dir, check_sha=check_sha),
        )


class APIResult(t.NamedTuple):
    """
    Flysight firmware API result container.

    See: https://github.com/flysight/flysight-2-firmware/blob/develop/Docs/firmware.md for the full
    API documentation.
    """

    device: Device
    include_beta: bool
    recommended: Firmware
    firmwares: list[Firmware]

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        """
        Build an `APIResult` instance from the firmware API response.

        The following keys are expected to be present in the response:
            * `device`
            * `include_beta`
            * `recommended`
            * `firmwares`

        Any other fields, if present, are ignored.

        Expected fields for each subcomponent are detailed in the API documentation and in the
        `from_raw` methods of the subcomponent classes.
        """
        return cls(
            device=Device.from_raw(raw_json["device"]),
            include_beta=raw_json["include_beta"],
            recommended=Firmware.from_raw(raw_json["recommended"]),
            firmwares=[Firmware.from_raw(f) for f in raw_json["firmwares"]],
        )


def fetch_available_firmware(device_info: str, include_beta: bool = False) -> APIResult:
    """
    Fetch available firmware for the Flysight device.

    `device_info` is expected to be the full, unaltered contents of `FLYSIGHT.TXT`, which should be
    located at the root of the device.

    The `include_beta` flag may be set to `True` to retrieve any available beta firmware releases.

    See: https://github.com/flysight/flysight-2-firmware/blob/develop/Docs/firmware.md for the full
    API documentation.
    """
    with niquests.Session() as s:
        r = s.post(
            url=API_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"flysight_txt": device_info}),  # API expects json-encoded data
            params={"include_beta": str(include_beta)},
        )
        r.raise_for_status()

        firmware_info = r.json()

    return APIResult.from_raw(firmware_info)
