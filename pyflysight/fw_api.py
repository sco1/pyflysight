import json
import typing as t

import niquests

API_URL = "https://flysight.ca/wp-json/flysight/v1/firmware"


class Device(t.NamedTuple):
    firmware_version: str
    stack_version: str
    stack_version_unknown: bool
    pubkey_x: str
    legacy: bool

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        return cls(
            firmware_version=raw_json["firmware_version"],
            stack_version=raw_json["stack_version"],
            stack_version_unknown=raw_json["stack_version_unknown"],
            pubkey_x=raw_json["pubkey_x"],
            legacy=raw_json["legacy"],
        )


class FileObject(t.NamedTuple):
    url: str
    target_path: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        return cls(
            url=raw_json["url"],
            target_path=raw_json["target_path"],
            size_bytes=raw_json["size_bytes"],
            sha256=raw_json["sha256"],
        )


class Stack(t.NamedTuple):
    required_version: str
    current_version: str
    current_version_unknown: bool
    update_required: bool
    file: FileObject | None

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
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


class Firmware(t.NamedTuple):
    version: str
    release_date: str
    is_beta: bool
    release_notes_url: str | None
    firmware: FileObject
    stack: Stack

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
        return cls(
            version=raw_json["version"],
            release_date=raw_json["release_date"],
            is_beta=raw_json["is_beta"],
            release_notes_url=raw_json["release_notes_url"],
            firmware=FileObject.from_raw(raw_json["firmware"]),
            stack=Stack.from_raw(raw_json["stack"]),
        )


class APIResult(t.NamedTuple):
    device: Device
    include_beta: bool
    recommended: Firmware
    firmwares: list[Firmware]

    @classmethod
    def from_raw(cls, raw_json: dict) -> t.Self:
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
