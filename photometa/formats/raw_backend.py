from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from importlib.metadata import (
    PackageNotFoundError,
    version,
)
from pathlib import Path
from types import ModuleType

from photometa.hashing import (
    HashingError,
    calculate_sha256,
)

FORMAT_RAW = "RAW"


RAW_EXTENSIONS = frozenset(
    {
        ".3fr",
        ".arw",
        ".cr2",
        ".cr3",
        ".dcr",
        ".dng",
        ".erf",
        ".fff",
        ".iiq",
        ".kdc",
        ".mef",
        ".mos",
        ".mrw",
        ".nef",
        ".nrw",
        ".orf",
        ".ori",
        ".pef",
        ".raf",
        ".raw",
        ".rw2",
        ".rwl",
        ".sr2",
        ".srf",
        ".srw",
        ".x3f",
    }
)


class RawSupportError(Exception):
    """Base exception for RAW support."""


class RawBackendUnavailable(
    RawSupportError
):
    """Optional rawpy backend is unavailable."""


class RawInspectionError(
    RawSupportError
):
    """RAW image could not be inspected."""


@dataclass(frozen=True)
class RawBackendInfo:
    rawpy_version: str

    libraw_version: str

    enabled_features: tuple[
        str,
        ...
    ]


@dataclass(frozen=True)
class RawImageSnapshot:
    path: Path

    format: str
    variant: str

    backend: str
    support_level: str

    rawpy_version: str
    libraw_version: str

    size_bytes: int

    sha256: str

    raw_width: int
    raw_height: int

    visible_width: int
    visible_height: int

    top_margin: int
    left_margin: int

    crop_width: int
    crop_height: int

    pixel_aspect: float

    orientation_code: int

    raw_type: str

    num_colors: int

    color_description: str | None

    white_level: int | None

    black_level_per_channel: (
        tuple[int, ...]
        | None
    )

    camera_white_level_per_channel: (
        tuple[int, ...]
        | None
    )

    camera_white_balance: (
        tuple[float, ...]
        | None
    )

    daylight_white_balance: (
        tuple[float, ...]
        | None
    )

    iso_speed: float | None

    shutter_speed: float | None

    aperture: float | None

    focal_length: float | None

    timestamp: datetime | None

    shot_order: int | None

    artist: str | None

    lens_make: str | None
    lens_model: str | None

    lens_min_focal: float | None
    lens_max_focal: float | None

    enabled_features: tuple[
        str,
        ...
    ]

    warnings: tuple[
        str,
        ...
    ]

    @property
    def raw_resolution(
        self,
    ) -> str:

        return (
            f"{self.raw_width}x"
            f"{self.raw_height}"
        )

    @property
    def visible_resolution(
        self,
    ) -> str:

        return (
            f"{self.visible_width}x"
            f"{self.visible_height}"
        )


def is_raw_candidate_path(
    path: str | Path,
) -> bool:
    """
    Extension-based candidate filter only.

    The extension does not prove that the
    file is valid RAW. LibRaw performs the
    actual validation.
    """

    file_path = Path(
        path
    )

    return (
        file_path.suffix.casefold()
        in RAW_EXTENSIONS
    )


def raw_backend_available() -> bool:

    try:

        import_module(
            "rawpy"
        )

    except ModuleNotFoundError:

        return False

    return True


def get_raw_backend_info(
) -> RawBackendInfo:

    rawpy = (
        _load_rawpy()
    )

    try:

        rawpy_version = version(
            "rawpy"
        )

    except PackageNotFoundError:

        rawpy_version = (
            "unknown"
        )

    libraw_version_value = getattr(
        rawpy,
        "libraw_version",
        (),
    )

    libraw_version = (
        ".".join(
            str(value)
            for value
            in libraw_version_value
        )
        if libraw_version_value
        else "unknown"
    )

    flags = getattr(
        rawpy,
        "flags",
        None,
    )

    enabled_features: tuple[
        str,
        ...
    ] = ()

    if isinstance(
        flags,
        dict,
    ):

        enabled_features = tuple(
            sorted(
                str(name)
                for name, enabled
                in flags.items()
                if enabled is True
            )
        )

    return RawBackendInfo(
        rawpy_version=(
            rawpy_version
        ),
        libraw_version=(
            libraw_version
        ),
        enabled_features=(
            enabled_features
        ),
    )


def probe_raw_file(
    path: str | Path,
) -> bool:
    """
    Validate a RAW candidate with LibRaw.

    This does not call postprocess().
    """

    file_path = Path(
        path
    )

    if not is_raw_candidate_path(
        file_path
    ):

        return False

    rawpy = (
        _load_rawpy()
    )

    try:

        with rawpy.imread(
            str(file_path)
        ):

            return True

    except (
        rawpy.LibRawError,
        OSError,
        ValueError,
    ):

        return False


def inspect_raw_image(
    path: str | Path,
) -> RawImageSnapshot:

    file_path = Path(
        path
    )

    if not file_path.exists():

        raise RawInspectionError(
            (
                "File does not exist: "
                f"{file_path}"
            )
        )

    if not file_path.is_file():

        raise RawInspectionError(
            (
                "Path is not a file: "
                f"{file_path}"
            )
        )

    rawpy = (
        _load_rawpy()
    )

    backend_info = (
        get_raw_backend_info()
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

        raise RawInspectionError(
            (
                "Could not inspect RAW "
                f"file information: {exc}"
            )
        ) from exc

    warnings: list[
        str
    ] = []

    try:

        with rawpy.imread(
            str(file_path)
        ) as raw:

            #
            # Parse/unpack the sensor data
            # through LibRaw.
            #
            # We intentionally DO NOT call
            # postprocess(), demosaic the
            # image or copy raw_image.
            #
            raw.unpack()

            sizes = raw.sizes

            other = raw.other

            lens = raw.lens

            raw_type_value = (
                raw.raw_type
            )

            raw_type = getattr(
                raw_type_value,
                "name",
                str(raw_type_value),
            )

            num_colors = int(
                raw.num_colors
            )

            color_description = (
                _decode_color_description(
                    raw.color_desc
                )
            )

            white_level = (
                _positive_int_or_none(
                    raw.white_level
                )
            )

            black_levels = (
                _int_tuple_or_none(
                    raw.black_level_per_channel,
                    allow_zero=True,
                )
            )

            camera_white_levels = (
                _int_tuple_or_none(
                    (
                        raw
                        .camera_white_level_per_channel
                    ),
                    allow_zero=True,
                )
            )

            camera_wb = (
                _float_tuple_or_none(
                    raw.camera_whitebalance
                )
            )

            daylight_wb = (
                _float_tuple_or_none(
                    raw.daylight_whitebalance
                )
            )

    except rawpy.LibRawError as exc:

        raise RawInspectionError(
            (
                "LibRaw could not decode "
                f"this RAW file: {exc}"
            )
        ) from exc

    except (
        OSError,
        ValueError,
        RuntimeError,
    ) as exc:

        raise RawInspectionError(
            (
                "Could not inspect RAW "
                f"image: {exc}"
            )
        ) from exc

    timestamp = (
        other.timestamp
        if (
            isinstance(
                other.timestamp,
                datetime,
            )
            and other.timestamp.year
            > 1971
        )
        else None
    )

    variant = (
        file_path.suffix[
            1:
        ].upper()
        if file_path.suffix
        else "RAW"
    )

    return RawImageSnapshot(
        path=file_path.resolve(),
        format=FORMAT_RAW,
        variant=variant,
        backend=(
            "rawpy / LibRaw"
        ),
        support_level=(
            "OPTIONAL / BASIC"
        ),
        rawpy_version=(
            backend_info.rawpy_version
        ),
        libraw_version=(
            backend_info.libraw_version
        ),
        size_bytes=size_bytes,
        sha256=sha256,
        raw_width=int(
            sizes.raw_width
        ),
        raw_height=int(
            sizes.raw_height
        ),
        visible_width=int(
            sizes.width
        ),
        visible_height=int(
            sizes.height
        ),
        top_margin=int(
            sizes.top_margin
        ),
        left_margin=int(
            sizes.left_margin
        ),
        crop_width=int(
            sizes.crop_width
        ),
        crop_height=int(
            sizes.crop_height
        ),
        pixel_aspect=float(
            sizes.pixel_aspect
        ),
        orientation_code=int(
            sizes.flip
        ),
        raw_type=raw_type,
        num_colors=num_colors,
        color_description=(
            color_description
        ),
        white_level=(
            white_level
        ),
        black_level_per_channel=(
            black_levels
        ),
        camera_white_level_per_channel=(
            camera_white_levels
        ),
        camera_white_balance=(
            camera_wb
        ),
        daylight_white_balance=(
            daylight_wb
        ),
        iso_speed=(
            _positive_float_or_none(
                other.iso_speed
            )
        ),
        shutter_speed=(
            _positive_float_or_none(
                other.shutter_speed
            )
        ),
        aperture=(
            _positive_float_or_none(
                other.aperture
            )
        ),
        focal_length=(
            _positive_float_or_none(
                other.focal_length
            )
        ),
        timestamp=timestamp,
        shot_order=(
            _nonnegative_int_or_none(
                other.shot_order
            )
        ),
        artist=(
            _text_or_none(
                other.artist
            )
        ),
        lens_make=(
            _text_or_none(
                lens.make
            )
        ),
        lens_model=(
            _text_or_none(
                lens.model
            )
        ),
        lens_min_focal=(
            _positive_float_or_none(
                lens.min_focal
            )
        ),
        lens_max_focal=(
            _positive_float_or_none(
                lens.max_focal
            )
        ),
        enabled_features=(
            backend_info
            .enabled_features
        ),
        warnings=tuple(
            warnings
        ),
    )


def _load_rawpy(
) -> ModuleType:

    try:

        return import_module(
            "rawpy"
        )

    except ModuleNotFoundError as exc:

        raise RawBackendUnavailable(
            (
                "RAW support requires "
                "the optional rawpy / "
                "LibRaw backend. Install "
                "PhotoMeta with: "
                "pip install -e "
                "\".[raw]\""
            )
        ) from exc


def _decode_color_description(
    value: object,
) -> str | None:

    if isinstance(
        value,
        bytes,
    ):

        text = value.decode(
            "ascii",
            errors="replace",
        )

    elif isinstance(
        value,
        str,
    ):

        text = value

    else:

        return None

    text = (
        text
        .replace(
            "\x00",
            "",
        )
        .strip()
    )

    return (
        text
        if text
        else None
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


def _positive_float_or_none(
    value: object,
) -> float | None:

    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):

        return None

    number = float(
        value
    )

    if number <= 0:

        return None

    return number


def _positive_int_or_none(
    value: object,
) -> int | None:

    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):

        return None

    number = int(
        value
    )

    if number <= 0:

        return None

    return number


def _nonnegative_int_or_none(
    value: object,
) -> int | None:

    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):

        return None

    number = int(
        value
    )

    if number < 0:

        return None

    return number


def _int_tuple_or_none(
    value: object,
    *,
    allow_zero: bool,
) -> tuple[int, ...] | None:

    if value is None:

        return None

    try:

        result = tuple(
            int(item)
            for item
            in value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if not result:

        return None

    if not allow_zero and not any(
        item > 0
        for item
        in result
    ):

        return None

    return result


def _float_tuple_or_none(
    value: object,
) -> tuple[float, ...] | None:

    if value is None:

        return None

    try:

        result = tuple(
            float(item)
            for item
            in value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if not result:

        return None

    if not any(
        item > 0
        for item
        in result
    ):

        return None

    return result
