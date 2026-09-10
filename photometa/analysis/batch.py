from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from photometa.analysis.comparison import (
    PRESENCE_NO,
    PRESENCE_YES,
    ComparisonError,
    inspect_image_for_comparison,
)
from photometa.analysis.privacy import (
    analyze_privacy,
)
from photometa.analysis.privacy_score import (
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MEDIUM,
    calculate_privacy_exposure_score,
)
from photometa.parsers.iptc import (
    IptcParserError,
)
from photometa.parsers.jpeg import (
    JpegParserError,
)
from photometa.parsers.xmp import (
    XmpParserError,
)


FORMAT_JPEG = "JPEG"
FORMAT_PNG = "PNG"
FORMAT_WEBP = "WEBP"
FORMAT_TIFF = "TIFF"
FORMAT_UNSUPPORTED = "UNSUPPORTED"


JPEG_SIGNATURE = b"\xFF\xD8"

PNG_SIGNATURE = (
    b"\x89PNG\r\n\x1a\n"
)

TIFF_LE_SIGNATURE = (
    b"II\x2A\x00"
)

TIFF_BE_SIGNATURE = (
    b"MM\x00\x2A"
)


class BatchAnalysisError(Exception):
    """Base exception for batch analysis errors."""


@dataclass(frozen=True)
class BatchFileResult:
    path: Path

    detected_format: str

    size_bytes: int | None = None

    sha256: str | None = None

    width: int | None = None
    height: int | None = None

    jpeg_process: str | None = None

    exif_status: str | None = None
    gps_status: str | None = None
    xmp_status: str | None = None
    iptc_status: str | None = None
    icc_status: str | None = None

    camera_model: str | None = None

    gps_detected: bool | None = None

    privacy_points: int | None = None

    privacy_level: str | None = None

    error: str | None = None

    @property
    def analyzed_successfully(
        self,
    ) -> bool:

        return (
            self.detected_format
            == FORMAT_JPEG
            and self.error is None
            and self.privacy_level
            is not None
        )


@dataclass(frozen=True)
class BatchReport:
    root: Path

    recursive: bool

    items: tuple[
        BatchFileResult,
        ...
    ]

    @property
    def total_files(
        self,
    ) -> int:

        return len(
            self.items
        )

    @property
    def jpeg_count(
        self,
    ) -> int:

        return sum(
            item.detected_format
            == FORMAT_JPEG
            for item in self.items
        )

    @property
    def png_count(
        self,
    ) -> int:

        return sum(
            item.detected_format
            == FORMAT_PNG
            for item in self.items
        )

    @property
    def webp_count(
        self,
    ) -> int:

        return sum(
            item.detected_format
            == FORMAT_WEBP
            for item in self.items
        )

    @property
    def tiff_count(
        self,
    ) -> int:

        return sum(
            item.detected_format
            == FORMAT_TIFF
            for item in self.items
        )

    @property
    def unsupported_count(
        self,
    ) -> int:

        return sum(
            item.detected_format
            == FORMAT_UNSUPPORTED
            for item in self.items
        )

    @property
    def analyzed_jpeg_count(
        self,
    ) -> int:

        return sum(
            item.analyzed_successfully
            for item in self.items
        )

    @property
    def failed_jpeg_count(
        self,
    ) -> int:

        return sum(
            (
                item.detected_format
                == FORMAT_JPEG
                and item.error is not None
            )
            for item in self.items
        )

    @property
    def gps_detected_count(
        self,
    ) -> int:

        return sum(
            item.gps_detected is True
            for item in self.items
        )

    @property
    def high_privacy_count(
        self,
    ) -> int:

        return self._privacy_count(
            LEVEL_HIGH
        )

    @property
    def medium_privacy_count(
        self,
    ) -> int:

        return self._privacy_count(
            LEVEL_MEDIUM
        )

    @property
    def low_privacy_count(
        self,
    ) -> int:

        return self._privacy_count(
            LEVEL_LOW
        )

    def _privacy_count(
        self,
        level: str,
    ) -> int:

        return sum(
            item.privacy_level
            == level
            for item in self.items
        )


def analyze_directory(
    path: str | Path,
    *,
    recursive: bool = False,
    exclude_paths: tuple[
        str | Path,
        ...
    ] = (),
) -> BatchReport:

    root = Path(
        path
    )

    if not root.exists():

        raise BatchAnalysisError(
            f"Directory does not exist: "
            f"{root}"
        )

    if not root.is_dir():

        raise BatchAnalysisError(
            f"Path is not a directory: "
            f"{root}"
        )

    root = root.resolve()

    excluded = {
        Path(
            current
        ).resolve()
        for current
        in exclude_paths
    }

    try:

        if recursive:

            candidates = (
                candidate
                for candidate
                in root.rglob("*")
                if candidate.is_file()
            )

        else:

            candidates = (
                candidate
                for candidate
                in root.iterdir()
                if candidate.is_file()
            )

        files = sorted(
            (
                candidate
                for candidate
                in candidates
                if candidate.resolve()
                not in excluded
            ),
            key=lambda item: (
                str(item).casefold()
            ),
        )

    except OSError as exc:

        raise BatchAnalysisError(
            (
                "Could not enumerate "
                f"directory {root}: {exc}"
            )
        ) from exc

    results = tuple(
        _analyze_batch_file(
            file_path
        )
        for file_path in files
    )

    return BatchReport(
        root=root,
        recursive=recursive,
        items=results,
    )


def detect_batch_file_format(
    path: str | Path,
) -> str:

    file_path = Path(
        path
    )

    try:

        with file_path.open(
            "rb"
        ) as file:

            signature = file.read(
                16
            )

    except OSError as exc:

        raise BatchAnalysisError(
            (
                "Could not read "
                f"{file_path}: {exc}"
            )
        ) from exc

    if signature.startswith(
        JPEG_SIGNATURE
    ):

        return FORMAT_JPEG

    if signature.startswith(
        PNG_SIGNATURE
    ):

        return FORMAT_PNG

    if (
        len(signature) >= 12
        and signature[0:4]
        == b"RIFF"
        and signature[8:12]
        == b"WEBP"
    ):

        return FORMAT_WEBP

    if (
        signature.startswith(
            TIFF_LE_SIGNATURE
        )
        or signature.startswith(
            TIFF_BE_SIGNATURE
        )
    ):

        return FORMAT_TIFF

    return FORMAT_UNSUPPORTED


def _analyze_batch_file(
    path: Path,
) -> BatchFileResult:

    try:

        size_bytes = (
            path.stat().st_size
        )

    except OSError:

        size_bytes = None

    try:

        detected_format = (
            detect_batch_file_format(
                path
            )
        )

    except BatchAnalysisError as exc:

        return BatchFileResult(
            path=path.resolve(),
            detected_format=(
                FORMAT_UNSUPPORTED
            ),
            size_bytes=size_bytes,
            error=str(
                exc
            ),
        )

    if (
        detected_format
        != FORMAT_JPEG
    ):

        return BatchFileResult(
            path=path.resolve(),
            detected_format=(
                detected_format
            ),
            size_bytes=size_bytes,
        )

    try:

        snapshot = (
            inspect_image_for_comparison(
                path
            )
        )

    except (
        ComparisonError,
        JpegParserError,
        OSError,
    ) as exc:

        return BatchFileResult(
            path=path.resolve(),
            detected_format=(
                FORMAT_JPEG
            ),
            size_bytes=size_bytes,
            error=str(
                exc
            ),
        )

    if (
        snapshot.gps
        == PRESENCE_YES
    ):

        gps_detected: (
            bool
            | None
        ) = True

    elif (
        snapshot.gps
        == PRESENCE_NO
    ):

        gps_detected = False

    else:

        gps_detected = None

    common = {
        "path": path.resolve(),
        "detected_format": (
            FORMAT_JPEG
        ),
        "size_bytes": (
            snapshot.size_bytes
        ),
        "sha256": (
            snapshot.sha256
        ),
        "width": (
            snapshot.width
        ),
        "height": (
            snapshot.height
        ),
        "jpeg_process": (
            snapshot.jpeg_process
        ),
        "exif_status": (
            snapshot.exif
        ),
        "gps_status": (
            snapshot.gps
        ),
        "xmp_status": (
            snapshot.xmp
        ),
        "iptc_status": (
            snapshot.iptc
        ),
        "icc_status": (
            snapshot.icc
        ),
        "camera_model": (
            snapshot.camera_model
        ),
        "gps_detected": (
            gps_detected
        ),
    }

    try:

        privacy_report = (
            analyze_privacy(
                path
            )
        )

        privacy_score = (
            calculate_privacy_exposure_score(
                privacy_report
            )
        )

    except (
        JpegParserError,
        XmpParserError,
        IptcParserError,
        OSError,
    ) as exc:

        return BatchFileResult(
            **common,
            error=str(
                exc
            ),
        )

    return BatchFileResult(
        **common,
        privacy_points=(
            privacy_score.points
        ),
        privacy_level=(
            privacy_score.level
        ),
    )
