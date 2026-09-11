from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from photometa.hashing import (
    HashingError,
    calculate_sha256,
)


BACKEND_NAME = "exiftool"

DEFAULT_TIMEOUT_SECONDS = 30


PRESENCE_YES = "YES"
PRESENCE_NO = "NO"


class ExifToolBackendError(Exception):
    """Base exception for the ExifTool backend."""


class ExifToolUnavailableError(
    ExifToolBackendError
):
    """ExifTool executable was not found."""


class ExifToolExecutionError(
    ExifToolBackendError
):
    """ExifTool could not inspect the file."""


class ExifToolOutputError(
    ExifToolBackendError
):
    """ExifTool returned unusable JSON output."""


@dataclass(frozen=True)
class ExifToolSnapshot:
    path: Path

    backend: str
    exiftool_version: str

    file_type: str | None
    mime_type: str | None

    size_bytes: int
    sha256: str

    width: int | None
    height: int | None

    tag_count: int

    group_counts: tuple[
        tuple[str, int],
        ...
    ]

    exif_status: str
    gps_status: str
    xmp_status: str
    iptc_status: str
    icc_status: str
    quicktime_status: str

    camera_make: str | None
    camera_model: str | None
    software: str | None

    datetime_original: str | None

    lens_make: str | None
    lens_model: str | None

    orientation: str | None

    warnings: tuple[
        str,
        ...
    ]

    @property
    def resolution(
        self,
    ) -> str | None:

        if (
            self.width is None
            or self.height is None
        ):

            return None

        return (
            f"{self.width}x"
            f"{self.height}"
        )


def exiftool_available(
) -> bool:

    return (
        shutil.which(
            "exiftool"
        )
        is not None
    )


def get_exiftool_version(
) -> str:

    executable = (
        _find_exiftool()
    )

    try:

        result = subprocess.run(
            [
                executable,
                "-ver",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )

    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:

        raise ExifToolExecutionError(
            (
                "Could not execute "
                f"ExifTool: {exc}"
            )
        ) from exc

    if result.returncode != 0:

        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or (
                "ExifTool version command "
                "failed."
            )
        )

        raise ExifToolExecutionError(
            message
        )

    version = (
        result.stdout.strip()
    )

    if not version:

        raise ExifToolOutputError(
            (
                "ExifTool did not return "
                "a version number."
            )
        )

    return version


def inspect_with_exiftool(
    path: str | Path,
) -> ExifToolSnapshot:

    file_path = Path(
        path
    )

    if not file_path.exists():

        raise ExifToolExecutionError(
            (
                "File does not exist: "
                f"{file_path}"
            )
        )

    if not file_path.is_file():

        raise ExifToolExecutionError(
            (
                "Path is not a file: "
                f"{file_path}"
            )
        )

    file_path = (
        file_path.resolve()
    )

    executable = (
        _find_exiftool()
    )

    try:

        size_bytes = (
            file_path.stat().st_size
        )

        sha256 = (
            calculate_sha256(
                file_path
            )
        )

    except (
        OSError,
        HashingError,
    ) as exc:

        raise ExifToolExecutionError(
            (
                "Could not inspect file "
                f"information: {exc}"
            )
        ) from exc

    version = (
        get_exiftool_version()
    )

    try:

        result = subprocess.run(
            [
                executable,
                "-j",
                "-G1",
                "-n",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=(
                DEFAULT_TIMEOUT_SECONDS
            ),
            check=False,
        )

    except subprocess.TimeoutExpired as exc:

        raise ExifToolExecutionError(
            (
                "ExifTool inspection timed "
                "out after "
                f"{DEFAULT_TIMEOUT_SECONDS} "
                "seconds."
            )
        ) from exc

    except OSError as exc:

        raise ExifToolExecutionError(
            (
                "Could not execute "
                f"ExifTool: {exc}"
            )
        ) from exc

    if result.returncode != 0:

        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or (
                "ExifTool failed with "
                f"exit code "
                f"{result.returncode}."
            )
        )

        raise ExifToolExecutionError(
            message
        )

    payload = (
        _parse_json_output(
            result.stdout
        )
    )

    warnings: list[
        str
    ] = []

    if result.stderr.strip():

        warnings.extend(
            line.strip()
            for line
            in result.stderr.splitlines()
            if line.strip()
        )

    warnings.extend(
        _collect_payload_warnings(
            payload
        )
    )

    group_counts = (
        _build_group_counts(
            payload
        )
    )

    groups = {
        group
        for group, _count
        in group_counts
    }

    tag_names = {
        _tag_name(
            key
        )
        for key
        in payload
        if key != "SourceFile"
    }

    exif_present = (
        _has_exif_groups(
            groups
        )
    )

    gps_present = any(
        name.startswith(
            "GPS"
        )
        for name
        in tag_names
    )

    xmp_present = any(
        group.startswith(
            "XMP"
        )
        for group
        in groups
    )

    iptc_present = any(
        group.startswith(
            "IPTC"
        )
        for group
        in groups
    )

    icc_present = any(
        group.startswith(
            "ICC"
        )
        for group
        in groups
    )

    quicktime_present = any(
        group.startswith(
            "QuickTime"
        )
        for group
        in groups
    )

    (
        image_width,
        image_height,
    ) = _select_resolution(
        payload
    )

    return ExifToolSnapshot(
        path=file_path,
        backend="ExifTool",
        exiftool_version=version,
        file_type=(
            _text_or_none(
                _first_tag(
                    payload,
                    "FileType",
                )
            )
        ),
        mime_type=(
            _text_or_none(
                _first_tag(
                    payload,
                    "MIMEType",
                )
            )
        ),
        size_bytes=size_bytes,
        sha256=sha256,
        width=image_width,
        height=image_height,
        tag_count=sum(
            1
            for key
            in payload
            if key != "SourceFile"
        ),
        group_counts=(
            group_counts
        ),
        exif_status=(
            _presence(
                exif_present
            )
        ),
        gps_status=(
            _presence(
                gps_present
            )
        ),
        xmp_status=(
            _presence(
                xmp_present
            )
        ),
        iptc_status=(
            _presence(
                iptc_present
            )
        ),
        icc_status=(
            _presence(
                icc_present
            )
        ),
        quicktime_status=(
            _presence(
                quicktime_present
            )
        ),
        camera_make=(
            _text_or_none(
                _first_tag(
                    payload,
                    "Make",
                )
            )
        ),
        camera_model=(
            _text_or_none(
                _first_tag(
                    payload,
                    "Model",
                    "CameraModelName",
                )
            )
        ),
        software=(
            _text_or_none(
                _first_tag(
                    payload,
                    "Software",
                )
            )
        ),
        datetime_original=(
            _text_or_none(
                _first_tag(
                    payload,
                    "DateTimeOriginal",
                )
            )
        ),
        lens_make=(
            _text_or_none(
                _first_tag(
                    payload,
                    "LensMake",
                )
            )
        ),
        lens_model=(
            _text_or_none(
                _first_tag(
                    payload,
                    "LensModel",
                    "LensID",
                )
            )
        ),
        orientation=(
            _text_or_none(
                _first_tag(
                    payload,
                    "Orientation",
                )
            )
        ),
        warnings=tuple(
            dict.fromkeys(
                warnings
            )
        ),
    )


def _find_exiftool(
) -> str:

    executable = (
        shutil.which(
            "exiftool"
        )
    )

    if executable is None:

        raise ExifToolUnavailableError(
            (
                "ExifTool backend is not "
                "installed or is not available "
                "in PATH. On Debian/Ubuntu, "
                "install package "
                "'libimage-exiftool-perl'."
            )
        )

    return executable


def _parse_json_output(
    text: str,
) -> dict[
    str,
    Any,
]:

    if not text.strip():

        raise ExifToolOutputError(
            (
                "ExifTool returned empty "
                "JSON output."
            )
        )

    try:

        document = json.loads(
            text
        )

    except json.JSONDecodeError as exc:

        raise ExifToolOutputError(
            (
                "ExifTool returned invalid "
                f"JSON: {exc}"
            )
        ) from exc

    if not isinstance(
        document,
        list,
    ):

        raise ExifToolOutputError(
            (
                "Expected an ExifTool JSON "
                "array."
            )
        )

    if len(document) != 1:

        raise ExifToolOutputError(
            (
                "Expected metadata for "
                "exactly one file."
            )
        )

    payload = document[0]

    if not isinstance(
        payload,
        dict,
    ):

        raise ExifToolOutputError(
            (
                "ExifTool JSON item is not "
                "an object."
            )
        )

    return payload


def _build_group_counts(
    payload: dict[
        str,
        Any,
    ],
) -> tuple[
    tuple[str, int],
    ...
]:

    counts: dict[
        str,
        int,
    ] = {}

    for key in payload:

        if key == "SourceFile":

            continue

        group = (
            _group_name(
                key
            )
        )

        counts[group] = (
            counts.get(
                group,
                0,
            )
            + 1
        )

    return tuple(
        sorted(
            counts.items(),
            key=lambda item: (
                item[0].casefold()
            ),
        )
    )


def _group_name(
    key: str,
) -> str:

    if ":" not in key:

        return "Other"

    group, _name = (
        key.split(
            ":",
            1,
        )
    )

    return group


def _tag_name(
    key: str,
) -> str:

    if ":" not in key:

        return key

    _group, name = (
        key.split(
            ":",
            1,
        )
    )

    return name


def _select_resolution(
    payload: dict[
        str,
        Any,
    ],
) -> tuple[
    int | None,
    int | None,
]:
    """
    Select width and height as a pair.

    ExifTool may expose multiple image
    representations from one file.

    Examples include:
    - primary raster dimensions
    - RAW SubIFD dimensions
    - embedded previews
    - metadata-declared crop dimensions

    Never choose width and height
    independently from unrelated groups.
    """

    candidates = (
        (
            "File:ImageWidth",
            "File:ImageHeight",
        ),
        (
            "SubIFD:ImageWidth",
            "SubIFD:ImageHeight",
        ),
        (
            "ExifIFD:ExifImageWidth",
            "ExifIFD:ExifImageHeight",
        ),
        (
            "QuickTime:ImageWidth",
            "QuickTime:ImageHeight",
        ),
        (
            "IFD0:ImageWidth",
            "IFD0:ImageHeight",
        ),
        (
            "XMP-tiff:ImageWidth",
            "XMP-tiff:ImageHeight",
        ),
        (
            "XMP-exif:ExifImageWidth",
            "XMP-exif:ExifImageHeight",
        ),
    )

    for (
        width_key,
        height_key,
    ) in candidates:

        width = _int_or_none(
            payload.get(
                width_key
            )
        )

        height = _int_or_none(
            payload.get(
                height_key
            )
        )

        if (
            width is not None
            and height is not None
            and width > 0
            and height > 0
        ):

            return (
                width,
                height,
            )

    #
    # Compatibility fallback for formats
    # whose ExifTool group was not covered
    # above. Even here, try to preserve a
    # width/height pair from the same group.
    #
    groups: dict[
        str,
        dict[str, Any],
    ] = {}

    for key, value in (
        payload.items()
    ):

        if ":" not in key:

            continue

        group, name = (
            key.split(
                ":",
                1,
            )
        )

        groups.setdefault(
            group,
            {}
        )[
            name
        ] = value

    for values in (
        groups.values()
    ):

        width = _int_or_none(
            values.get(
                "ImageWidth"
            )
        )

        height = _int_or_none(
            values.get(
                "ImageHeight"
            )
        )

        if (
            width is not None
            and height is not None
            and width > 0
            and height > 0
        ):

            return (
                width,
                height,
            )

    return (
        None,
        None,
    )


def _first_tag(
    payload: dict[
        str,
        Any,
    ],
    *names: str,
) -> Any:

    for name in names:

        if name in payload:

            return payload[
                name
            ]

        for key, value in (
            payload.items()
        ):

            if (
                _tag_name(
                    key
                )
                == name
            ):

                return value

    return None


def _has_exif_groups(
    groups: set[str],
) -> bool:

    for group in groups:

        if group in {
            "IFD0",
            "ExifIFD",
            "InteropIFD",
            "GPS",
        }:

            return True

        if group.startswith(
            "SubIFD"
        ):

            return True

    return False


def _collect_payload_warnings(
    payload: dict[
        str,
        Any,
    ],
) -> tuple[
    str,
    ...
]:

    warnings: list[
        str
    ] = []

    for key, value in (
        payload.items()
    ):

        name = (
            _tag_name(
                key
            )
        )

        if name not in {
            "Warning",
            "Error",
        }:

            continue

        text = (
            _text_or_none(
                value
            )
        )

        if text:

            warnings.append(
                text
            )

    return tuple(
        warnings
    )


def _presence(
    value: bool,
) -> str:

    return (
        PRESENCE_YES
        if value
        else PRESENCE_NO
    )


def _text_or_none(
    value: object,
) -> str | None:

    if value is None:

        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
        ),
    ):

        text = str(
            value
        ).strip()

        return (
            text
            if text
            else None
        )

    return None


def _int_or_none(
    value: object,
) -> int | None:

    if isinstance(
        value,
        bool,
    ):

        return None

    if isinstance(
        value,
        int,
    ):

        return value

    if isinstance(
        value,
        float,
    ):

        return int(
            value
        )

    if isinstance(
        value,
        str,
    ):

        try:

            return int(
                float(
                    value.strip()
                )
            )

        except ValueError:

            return None

    return None
