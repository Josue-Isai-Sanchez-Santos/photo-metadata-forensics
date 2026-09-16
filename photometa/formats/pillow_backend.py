from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import (
    Image,
    UnidentifiedImageError,
)

from photometa.hashing import (
    HashingError,
    calculate_sha256,
)
from photometa.interpretation.special_fields import (
    interpret_orientation,
)

FORMAT_JPEG = "JPEG"

SUPPORTED_PILLOW_FORMATS = {
    "PNG",
    "WEBP",
    "TIFF",
}

PRESENCE_YES = "YES"
PRESENCE_NO = "NO"
PRESENCE_UNKNOWN = "UNKNOWN"


TAG_MAKE = 0x010F
TAG_MODEL = 0x0110
TAG_ORIENTATION = 0x0112
TAG_SOFTWARE = 0x0131
TAG_ARTIST = 0x013B

TAG_DATETIME_ORIGINAL = 0x9003

TAG_EXIF_IFD_POINTER = 0x8769
TAG_GPS_IFD_POINTER = 0x8825


class AdditionalFormatError(Exception):
    """Error while inspecting an additional image format."""


@dataclass(frozen=True)
class AdditionalImageSnapshot:
    path: Path

    format: str
    mime_type: str

    size_bytes: int

    width: int
    height: int

    mode: str

    frame_count: int
    animated: bool

    sha256: str

    exif_status: str
    exif_gps_status: str
    xmp_status: str
    icc_status: str

    camera_make: str | None
    camera_model: str | None
    software: str | None
    artist: str | None

    datetime_original: str | None

    orientation_raw: object | None
    orientation_interpreted: str | None

    backend: str

    warnings: tuple[
        str,
        ...
    ]

    @property
    def resolution(
        self,
    ) -> str:

        return (
            f"{self.width}x"
            f"{self.height}"
        )


def detect_scan_format(
    path: str | Path,
) -> str:

    file_path = Path(
        path
    )

    if not file_path.exists():

        raise AdditionalFormatError(
            f"File does not exist: "
            f"{file_path}"
        )

    if not file_path.is_file():

        raise AdditionalFormatError(
            f"Path is not a file: "
            f"{file_path}"
        )

    try:

        with Image.open(
            file_path
        ) as image:

            format_name = (
                image.format
                or ""
            ).upper()

    except UnidentifiedImageError as exc:

        raise AdditionalFormatError(
            (
                "Unsupported or "
                f"unrecognized image: "
                f"{file_path}"
            )
        ) from exc

    except OSError as exc:

        raise AdditionalFormatError(
            (
                "Could not open image "
                f"{file_path}: {exc}"
            )
        ) from exc

    if format_name == "JPG":

        format_name = (
            FORMAT_JPEG
        )

    if not format_name:

        raise AdditionalFormatError(
            (
                "Image format could "
                "not be determined."
            )
        )

    return format_name


def inspect_additional_image(
    path: str | Path,
) -> AdditionalImageSnapshot:

    file_path = Path(
        path
    )

    format_name = (
        detect_scan_format(
            file_path
        )
    )

    if (
        format_name
        not in SUPPORTED_PILLOW_FORMATS
    ):

        raise AdditionalFormatError(
            (
                f"{format_name} is not "
                "handled by the additional "
                "Pillow backend."
            )
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

        raise AdditionalFormatError(
            (
                "Could not inspect "
                f"file information: {exc}"
            )
        ) from exc

    warnings: list[
        str
    ] = []

    try:

        with Image.open(
            file_path
        ) as image:

            width, height = (
                image.size
            )

            mode = str(
                image.mode
            )

            frame_count = int(
                getattr(
                    image,
                    "n_frames",
                    1,
                )
            )

            animated = bool(
                getattr(
                    image,
                    "is_animated",
                    False,
                )
            )

            mime_type = (
                Image.MIME.get(
                    format_name,
                    (
                        "application/"
                        "octet-stream"
                    ),
                )
            )

            info = dict(
                image.info
            )

            (
                exif_status,
                exif_values,
                exif_object,
            ) = _read_exif(
                image,
                format_name,
                warnings,
            )

            gps_status = (
                _read_exif_gps_status(
                    exif_status,
                    exif_object,
                    warnings,
                )
            )

            xmp_status = (
                PRESENCE_YES
                if _has_xmp(info)
                else PRESENCE_NO
            )

            icc_status = (
                PRESENCE_YES
                if bool(
                    info.get(
                        "icc_profile"
                    )
                )
                else PRESENCE_NO
            )

    except (
        UnidentifiedImageError,
        OSError,
    ) as exc:

        raise AdditionalFormatError(
            (
                "Could not inspect "
                f"{format_name}: {exc}"
            )
        ) from exc

    orientation_raw = (
        exif_values.get(
            TAG_ORIENTATION
        )
    )

    orientation_interpreted = None

    if orientation_raw is not None:

        orientation_interpreted = (
            interpret_orientation(
                orientation_raw
            )
        )

    return AdditionalImageSnapshot(
        path=file_path.resolve(),
        format=format_name,
        mime_type=mime_type,
        size_bytes=size_bytes,
        width=width,
        height=height,
        mode=mode,
        frame_count=frame_count,
        animated=animated,
        sha256=sha256,
        exif_status=(
            exif_status
        ),
        exif_gps_status=(
            gps_status
        ),
        xmp_status=xmp_status,
        icc_status=icc_status,
        camera_make=(
            _text_or_none(
                exif_values.get(
                    TAG_MAKE
                )
            )
        ),
        camera_model=(
            _text_or_none(
                exif_values.get(
                    TAG_MODEL
                )
            )
        ),
        software=(
            _text_or_none(
                exif_values.get(
                    TAG_SOFTWARE
                )
            )
        ),
        artist=(
            _text_or_none(
                exif_values.get(
                    TAG_ARTIST
                )
            )
        ),
        datetime_original=(
            _text_or_none(
                exif_values.get(
                    TAG_DATETIME_ORIGINAL
                )
            )
        ),
        orientation_raw=(
            orientation_raw
        ),
        orientation_interpreted=(
            orientation_interpreted
        ),
        backend="Pillow",
        warnings=tuple(
            warnings
        ),
    )


def _read_exif(
    image: Image.Image,
    format_name: str,
    warnings: list[str],
) -> tuple[
    str,
    dict[int, object],
    object | None,
]:

    try:

        exif = image.getexif()

    except Exception as exc:

        warnings.append(
            (
                "Pillow could not read "
                f"EXIF metadata: {exc}"
            )
        )

        return (
            PRESENCE_UNKNOWN,
            {},
            None,
        )

    values = dict(
        exif.items()
    )

    #
    # TIFF itself is based on IFDs.
    #
    # Pillow may therefore return normal
    # TIFF tags through getexif() even when
    # no ExifIFD extension exists.
    #
    # For TIFF, EXIF=YES must mean that an
    # actual ExifIFD is present, not merely
    # that baseline TIFF tags exist.
    #
    if format_name == "TIFF":

        get_ifd = getattr(
            exif,
            "get_ifd",
            None,
        )

        if get_ifd is None:

            warnings.append(
                (
                    "Pillow does not expose "
                    "ExifIFD inspection for "
                    "this TIFF image."
                )
            )

            return (
                PRESENCE_UNKNOWN,
                values,
                exif,
            )

        try:

            exif_ifd = get_ifd(
                TAG_EXIF_IFD_POINTER
            )

        except Exception as exc:

            warnings.append(
                (
                    "Pillow could not inspect "
                    f"the TIFF ExifIFD: {exc}"
                )
            )

            return (
                PRESENCE_UNKNOWN,
                values,
                exif,
            )

        return (
            (
                PRESENCE_YES
                if bool(
                    exif_ifd
                )
                else PRESENCE_NO
            ),
            values,
            exif,
        )

    return (
        (
            PRESENCE_YES
            if values
            else PRESENCE_NO
        ),
        values,
        exif,
    )


def _read_exif_gps_status(
    exif_status: str,
    exif: object | None,
    warnings: list[str],
) -> str:

    if (
        exif_status
        == PRESENCE_UNKNOWN
        or exif is None
    ):

        return PRESENCE_UNKNOWN

    get_ifd = getattr(
        exif,
        "get_ifd",
        None,
    )

    if get_ifd is None:

        return PRESENCE_UNKNOWN

    try:

        gps_ifd = get_ifd(
            TAG_GPS_IFD_POINTER
        )

    except Exception as exc:

        warnings.append(
            (
                "Pillow could not read "
                f"the EXIF GPS IFD: {exc}"
            )
        )

        return PRESENCE_UNKNOWN

    return (
        PRESENCE_YES
        if bool(
            gps_ifd
        )
        else PRESENCE_NO
    )


def _has_xmp(
    info: dict[
        object,
        object,
    ],
) -> bool:

    for key, value in (
        info.items()
    ):

        key_text = str(
            key
        ).casefold()

        if (
            "xmp" in key_text
            and value
        ):

            return True

    return False


def _text_or_none(
    value: object,
) -> str | None:

    if not isinstance(
        value,
        str,
    ):

        return None

    value = value.strip()

    return (
        value
        if value
        else None
    )
