from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType

from PIL import Image

from photometa.hashing import (
    HashingError,
    calculate_sha256,
)
from photometa.interpretation.special_fields import (
    interpret_orientation,
)


FORMAT_HEIC = "HEIC"
FORMAT_HEIF = "HEIF"


PRESENCE_YES = "YES"
PRESENCE_NO = "NO"
PRESENCE_UNKNOWN = "UNKNOWN"


#
# HEVC-based HEIF brands handled by
# pillow-heif's HEIF plugin.
#
HEIC_BRANDS = {
    b"heic",
    b"heix",
    b"heim",
    b"heis",
    b"hevc",
    b"hevx",
    b"hevm",
    b"hevs",
}

GENERIC_HEIF_BRANDS = {
    b"mif1",
    b"msf1",
}

HEIF_BRANDS = (
    HEIC_BRANDS
    | GENERIC_HEIF_BRANDS
)


#
# AVIF also uses ISO BMFF and may contain
# mif1 as a compatible brand.
#
# Point 27B is HEIC/HEIF only, so AVIF must
# not accidentally be classified as HEIF.
#
AVIF_BRANDS = {
    b"avif",
    b"avis",
}


TAG_MAKE = 0x010F
TAG_MODEL = 0x0110
TAG_ORIENTATION = 0x0112
TAG_SOFTWARE = 0x0131
TAG_ARTIST = 0x013B

TAG_EXIF_IFD_POINTER = 0x8769
TAG_GPS_IFD_POINTER = 0x8825

TAG_DATETIME_ORIGINAL = 0x9003


class HeifError(Exception):
    """Base exception for HEIC/HEIF support."""


class HeifBackendUnavailable(
    HeifError
):
    """Optional pillow-heif backend is unavailable."""


class HeifInspectionError(
    HeifError
):
    """HEIC/HEIF image could not be inspected."""


@dataclass(frozen=True)
class HeifContainerInfo:
    major_brand: str

    compatible_brands: tuple[
        str,
        ...
    ]

    format: str


@dataclass(frozen=True)
class HeifImageSnapshot:
    path: Path

    format: str
    mime_type: str

    major_brand: str

    compatible_brands: tuple[
        str,
        ...
    ]

    size_bytes: int

    width: int
    height: int

    mode: str

    image_count: int

    bit_depth: int | None
    chroma: int | None

    has_alpha: bool

    sha256: str

    exif_status: str
    exif_gps_status: str

    xmp_status: str

    icc_status: str
    nclx_status: str

    other_metadata_blocks: int

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


def detect_heif_container(
    path: str | Path,
) -> HeifContainerInfo | None:
    """
    Detects supported HEIC/HEIF ISO-BMFF
    brands without requiring pillow-heif.

    This is container recognition only.
    It does not decode the image.
    """

    file_path = Path(
        path
    )

    try:

        with file_path.open(
            "rb"
        ) as file:

            data = file.read(
                4096
            )

    except OSError as exc:

        raise HeifInspectionError(
            (
                "Could not read "
                f"{file_path}: {exc}"
            )
        ) from exc

    if len(data) < 16:

        return None

    box_size = int.from_bytes(
        data[0:4],
        byteorder="big",
    )

    if data[4:8] != b"ftyp":

        return None

    #
    # We intentionally support the normal
    # 32-bit ftyp box form here.
    #
    # Extended-size ftyp boxes are unusual
    # and are not claimed by Point 27B.
    #
    if box_size < 16:

        return None

    available_size = min(
        box_size,
        len(data),
    )

    major_brand = (
        data[8:12]
    )

    compatible: list[
        bytes
    ] = []

    offset = 16

    while (
        offset + 4
        <= available_size
    ):

        compatible.append(
            data[
                offset:
                offset + 4
            ]
        )

        offset += 4

    brands = {
        major_brand,
        *compatible,
    }

    #
    # Avoid classifying AVIF as generic
    # HEIF merely because it also lists
    # mif1 compatibility.
    #
    if (
        brands
        & AVIF_BRANDS
    ):

        return None

    if not (
        brands
        & HEIF_BRANDS
    ):

        return None

    if (
        brands
        & HEIC_BRANDS
    ):

        format_name = (
            FORMAT_HEIC
        )

    else:

        format_name = (
            FORMAT_HEIF
        )

    return HeifContainerInfo(
        major_brand=(
            _brand_text(
                major_brand
            )
        ),
        compatible_brands=tuple(
            _brand_text(
                brand
            )
            for brand
            in compatible
        ),
        format=format_name,
    )


def inspect_heif_image(
    path: str | Path,
) -> HeifImageSnapshot:

    file_path = Path(
        path
    )

    container = (
        detect_heif_container(
            file_path
        )
    )

    if container is None:

        raise HeifInspectionError(
            (
                "File is not a supported "
                "HEIC/HEIF container."
            )
        )

    pillow_heif = (
        _load_pillow_heif()
    )

    try:

        supported = (
            pillow_heif.is_supported(
                file_path
            )
        )

    except Exception as exc:

        raise HeifInspectionError(
            (
                "Could not verify HEIF "
                f"decoder support: {exc}"
            )
        ) from exc

    if not supported:

        raise HeifInspectionError(
            (
                "pillow-heif/libheif does "
                "not support decoding this "
                "HEIC/HEIF file."
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

        raise HeifInspectionError(
            (
                "Could not inspect HEIF "
                f"file information: {exc}"
            )
        ) from exc

    try:

        heif_file = (
            pillow_heif.open_heif(
                file_path,
                convert_hdr_to_8bit=False,
            )
        )

        width, height = (
            heif_file.size
        )

        mode = str(
            heif_file.mode
        )

        image_count = len(
            heif_file
        )

        has_alpha = bool(
            heif_file.has_alpha
        )

        info = dict(
            heif_file.info
        )

        mime_type = (
            pillow_heif
            .get_file_mimetype(
                file_path
            )
        )

    except (
        ValueError,
        EOFError,
        SyntaxError,
        RuntimeError,
        OSError,
        IndexError,
    ) as exc:

        raise HeifInspectionError(
            (
                "Could not inspect "
                f"HEIC/HEIF image: {exc}"
            )
        ) from exc

    if not mime_type:

        mime_type = (
            "image/heic"
            if container.format
            == FORMAT_HEIC
            else "image/heif"
        )

    exif_raw = (
        info.get(
            "exif"
        )
    )

    xmp_raw = (
        info.get(
            "xmp"
        )
    )

    icc_raw = (
        info.get(
            "icc_profile"
        )
    )

    nclx = (
        info.get(
            "nclx_profile"
        )
    )

    other_metadata = (
        info.get(
            "metadata"
        )
    )

    bit_depth = (
        info.get(
            "bit_depth"
        )
    )

    chroma = (
        info.get(
            "chroma"
        )
    )

    warnings: list[
        str
    ] = []

    exif_summary = (
        _read_exif_summary(
            exif_raw,
            warnings,
        )
    )

    orientation_raw = (
        exif_summary[
            "orientation"
        ]
    )

    orientation_interpreted = (
        None
    )

    if (
        orientation_raw
        is not None
    ):

        orientation_interpreted = (
            interpret_orientation(
                orientation_raw
            )
        )

    return HeifImageSnapshot(
        path=file_path.resolve(),
        format=container.format,
        mime_type=mime_type,
        major_brand=(
            container.major_brand
        ),
        compatible_brands=(
            container
            .compatible_brands
        ),
        size_bytes=size_bytes,
        width=width,
        height=height,
        mode=mode,
        image_count=image_count,
        bit_depth=(
            bit_depth
            if isinstance(
                bit_depth,
                int,
            )
            else None
        ),
        chroma=(
            chroma
            if isinstance(
                chroma,
                int,
            )
            else None
        ),
        has_alpha=has_alpha,
        sha256=sha256,
        exif_status=(
            PRESENCE_YES
            if exif_raw
            else PRESENCE_NO
        ),
        exif_gps_status=(
            exif_summary[
                "gps_status"
            ]
        ),
        xmp_status=(
            PRESENCE_YES
            if xmp_raw
            else PRESENCE_NO
        ),
        icc_status=(
            PRESENCE_YES
            if icc_raw
            else PRESENCE_NO
        ),
        nclx_status=(
            PRESENCE_YES
            if nclx
            else PRESENCE_NO
        ),
        other_metadata_blocks=(
            len(
                other_metadata
            )
            if isinstance(
                other_metadata,
                list,
            )
            else 0
        ),
        camera_make=(
            exif_summary[
                "make"
            ]
        ),
        camera_model=(
            exif_summary[
                "model"
            ]
        ),
        software=(
            exif_summary[
                "software"
            ]
        ),
        artist=(
            exif_summary[
                "artist"
            ]
        ),
        datetime_original=(
            exif_summary[
                "datetime_original"
            ]
        ),
        orientation_raw=(
            orientation_raw
        ),
        orientation_interpreted=(
            orientation_interpreted
        ),
        backend=(
            "pillow-heif / libheif"
        ),
        warnings=tuple(
            warnings
        ),
    )


def _load_pillow_heif(
) -> ModuleType:

    try:

        return import_module(
            "pillow_heif"
        )

    except ModuleNotFoundError as exc:

        raise HeifBackendUnavailable(
            (
                "HEIC/HEIF support requires "
                "the optional pillow-heif "
                "backend. Install PhotoMeta "
                "with: pip install -e "
                "\".[heif]\""
            )
        ) from exc


def _read_exif_summary(
    exif_raw: object,
    warnings: list[str],
) -> dict[
    str,
    object,
]:

    result: dict[
        str,
        object,
    ] = {
        "make": None,
        "model": None,
        "software": None,
        "artist": None,
        "datetime_original": None,
        "orientation": None,
        "gps_status": PRESENCE_NO,
    }

    if not isinstance(
        exif_raw,
        (
            bytes,
            bytearray,
        ),
    ):

        return result

    if not exif_raw:

        return result

    try:

        exif = Image.Exif()

        exif.load(
            bytes(
                exif_raw
            )
        )

        ifd0 = dict(
            exif.items()
        )

    except Exception as exc:

        warnings.append(
            (
                "HEIF EXIF metadata is "
                "present but selected fields "
                f"could not be decoded: {exc}"
            )
        )

        result[
            "gps_status"
        ] = PRESENCE_UNKNOWN

        return result

    result[
        "make"
    ] = _text_or_none(
        ifd0.get(
            TAG_MAKE
        )
    )

    result[
        "model"
    ] = _text_or_none(
        ifd0.get(
            TAG_MODEL
        )
    )

    result[
        "software"
    ] = _text_or_none(
        ifd0.get(
            TAG_SOFTWARE
        )
    )

    result[
        "artist"
    ] = _text_or_none(
        ifd0.get(
            TAG_ARTIST
        )
    )

    result[
        "orientation"
    ] = ifd0.get(
        TAG_ORIENTATION
    )

    try:

        exif_ifd = exif.get_ifd(
            TAG_EXIF_IFD_POINTER
        )

    except Exception as exc:

        warnings.append(
            (
                "Could not inspect the "
                f"HEIF ExifIFD: {exc}"
            )
        )

        exif_ifd = {}

    result[
        "datetime_original"
    ] = _text_or_none(
        exif_ifd.get(
            TAG_DATETIME_ORIGINAL
        )
    )

    try:

        gps_ifd = exif.get_ifd(
            TAG_GPS_IFD_POINTER
        )

    except Exception as exc:

        warnings.append(
            (
                "Could not inspect the "
                f"HEIF GPS IFD: {exc}"
            )
        )

        result[
            "gps_status"
        ] = PRESENCE_UNKNOWN

    else:

        result[
            "gps_status"
        ] = (
            PRESENCE_YES
            if bool(
                gps_ifd
            )
            else PRESENCE_NO
        )

    return result


def _brand_text(
    brand: bytes,
) -> str:

    return brand.decode(
        "ascii",
        errors="replace",
    )


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
