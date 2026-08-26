from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from photometa.extractors.gps_ifd import (
    GpsIfdExtractorError,
    extract_gps_ifd_from_jpeg,
)
from photometa.fileinfo import (
    FileInfoError,
    get_jpeg_dimensions,
)
from photometa.hashing import (
    calculate_sha256,
)
from photometa.parsers.icc import (
    ICC_IDENTIFIER,
)
from photometa.parsers.xmp import (
    EXTENDED_XMP_IDENTIFIER,
    XMP_IDENTIFIER,
)


class ScrubError(Exception):
    """Base exception for metadata scrubbing errors."""


@dataclass(frozen=True)
class RemovedSegment:
    marker: int
    marker_name: str
    offset: int
    size: int
    reason: str


@dataclass(frozen=True)
class ScrubReport:
    input_path: Path
    output_path: Path

    bytes_before: int
    bytes_after: int

    removed_segments: tuple[
        RemovedSegment,
        ...
    ]

    trailing_bytes_removed: int

    original_gps: bool
    sanitized_gps: bool

    dimensions_before: tuple[int, int]
    dimensions_after: tuple[int, int]

    original_sha256_before: str
    original_sha256_after: str
    sanitized_sha256: str

    image_data_sha256_before: str
    image_data_sha256_after: str

    @property
    def original_unchanged(
        self,
    ) -> bool:

        return (
            self.original_sha256_before
            == self.original_sha256_after
        )

    @property
    def dimensions_preserved(
        self,
    ) -> bool:

        return (
            self.dimensions_before
            == self.dimensions_after
        )

    @property
    def image_data_preserved(
        self,
    ) -> bool:

        return (
            self.image_data_sha256_before
            == self.image_data_sha256_after
        )

    @property
    def removed_bytes(
        self,
    ) -> int:

        return (
            self.bytes_before
            - self.bytes_after
        )


@dataclass(frozen=True)
class _RewriteResult:
    data: bytes

    removed_segments: tuple[
        RemovedSegment,
        ...
    ]

    trailing_bytes_removed: int
    scan_data_sha256: str


STANDALONE_MARKERS = {
    0x01,
    0xD8,
    0xD9,
    *range(
        0xD0,
        0xD8,
    ),
}


def default_output_path(
    path: str | Path,
) -> Path:

    input_path = Path(
        path
    )

    suffix = input_path.suffix

    if suffix:

        return input_path.with_name(
            (
                f"{input_path.stem}"
                f"_clean"
                f"{suffix}"
            )
        )

    return input_path.with_name(
        (
            f"{input_path.name}"
            "_clean.jpg"
        )
    )


def scrub_jpeg(
    path: str | Path,
    output: str | Path | None = None,
) -> ScrubReport:
    """
    Creates a sanitized JPEG copy.

    The original file is never modified.

    Privacy-bearing JPEG application
    metadata is removed while technical
    segments needed for rendering are
    preserved.

    The compressed image scan data is
    copied byte-for-byte.
    """

    input_path = Path(
        path
    )

    if not input_path.exists():

        raise ScrubError(
            f"Input file does not exist: "
            f"{input_path}"
        )

    if not input_path.is_file():

        raise ScrubError(
            f"Input path is not a file: "
            f"{input_path}"
        )

    output_path = (
        Path(output)
        if output is not None
        else default_output_path(
            input_path
        )
    )

    input_resolved = (
        input_path.resolve()
    )

    output_resolved = (
        output_path.resolve(
            strict=False
        )
    )

    if (
        input_resolved
        == output_resolved
    ):

        raise ScrubError(
            "Refusing to overwrite the "
            "original file."
        )

    if (
        output_path.exists()
        and os.path.samefile(
            input_path,
            output_path,
        )
    ):

        raise ScrubError(
            "Output refers to the same "
            "file as the input."
        )

    if output_path.exists():

        raise ScrubError(
            f"Output file already exists: "
            f"{output_path}"
        )

    if not output_path.parent.exists():

        raise ScrubError(
            f"Output directory does not exist: "
            f"{output_path.parent}"
        )

    try:

        dimensions_before = (
            get_jpeg_dimensions(
                input_path
            )
        )

    except FileInfoError as exc:

        raise ScrubError(
            f"Input JPEG validation failed: "
            f"{exc}"
        ) from exc

    original_sha256_before = (
        calculate_sha256(
            input_path
        )
    )

    original_gps = _has_gps(
        input_path
    )

    try:

        original_data = (
            input_path.read_bytes()
        )

    except OSError as exc:

        raise ScrubError(
            f"Could not read input file: "
            f"{exc}"
        ) from exc

    rewrite = _rewrite_jpeg_bytes(
        original_data
    )

    #
    # Verify the generated byte stream
    # before writing it to disk.
    #
    verification = (
        _rewrite_jpeg_bytes(
            rewrite.data
        )
    )

    if (
        verification.removed_segments
    ):

        raise ScrubError(
            "Sanitization verification "
            "failed: removable metadata "
            "remains in output."
        )

    if (
        verification.trailing_bytes_removed
        != 0
    ):

        raise ScrubError(
            "Sanitization verification "
            "failed: trailing data remains."
        )

    if (
        verification.data
        != rewrite.data
    ):

        raise ScrubError(
            "Sanitization is not "
            "idempotent."
        )

    if (
        verification.scan_data_sha256
        != rewrite.scan_data_sha256
    ):

        raise ScrubError(
            "Compressed image data changed "
            "during verification."
        )

    _atomic_write(
        output_path,
        rewrite.data,
    )

    try:

        dimensions_after = (
            get_jpeg_dimensions(
                output_path
            )
        )

        sanitized_gps = _has_gps(
            output_path
        )

        sanitized_sha256 = (
            calculate_sha256(
                output_path
            )
        )

        original_sha256_after = (
            calculate_sha256(
                input_path
            )
        )

    except Exception as exc:

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "Sanitized file verification "
            f"failed: {exc}"
        ) from exc

    if (
        original_sha256_before
        != original_sha256_after
    ):

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "Original file changed during "
            "the scrub operation."
        )

    if (
        dimensions_before
        != dimensions_after
    ):

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "Image dimensions changed "
            "during sanitization."
        )

    if sanitized_gps:

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "GPS metadata is still present "
            "after sanitization."
        )

    return ScrubReport(
        input_path=(
            input_resolved
        ),
        output_path=(
            output_path.resolve()
        ),
        bytes_before=len(
            original_data
        ),
        bytes_after=len(
            rewrite.data
        ),
        removed_segments=(
            rewrite.removed_segments
        ),
        trailing_bytes_removed=(
            rewrite.trailing_bytes_removed
        ),
        original_gps=(
            original_gps
        ),
        sanitized_gps=(
            sanitized_gps
        ),
        dimensions_before=(
            dimensions_before
        ),
        dimensions_after=(
            dimensions_after
        ),
        original_sha256_before=(
            original_sha256_before
        ),
        original_sha256_after=(
            original_sha256_after
        ),
        sanitized_sha256=(
            sanitized_sha256
        ),
        image_data_sha256_before=(
            rewrite.scan_data_sha256
        ),
        image_data_sha256_after=(
            verification.scan_data_sha256
        ),
    )


def _rewrite_jpeg_bytes(
    data: bytes,
) -> _RewriteResult:
    """
    Rewrites a complete JPEG while removing
    privacy-bearing metadata segments.

    The function understands entropy-coded
    scan regions well enough to preserve:

        FF00 byte stuffing
        RST0-RST7
        multiple SOS scans
        metadata between scans
        EOI

    It does not decode or re-encode pixels.
    """

    if (
        len(data) < 4
        or data[0:2]
        != b"\xFF\xD8"
    ):

        raise ScrubError(
            "File does not begin with "
            "JPEG SOI FF D8."
        )

    output = bytearray(
        data[0:2]
    )

    removed: list[
        RemovedSegment
    ] = []

    scan_hasher = hashlib.sha256()

    position = 2

    in_scan = False
    resume_scan = False

    saw_sos = False
    saw_eoi = False

    while position < len(data):

        if in_scan:

            marker_start = data.find(
                b"\xFF",
                position,
            )

            if marker_start == -1:

                raise ScrubError(
                    "JPEG scan data ended "
                    "without a marker."
                )

            scan_data = data[
                position:
                marker_start
            ]

            output += scan_data

            scan_hasher.update(
                scan_data
            )

            code_position = (
                marker_start
            )

            while (
                code_position
                < len(data)
                and data[
                    code_position
                ] == 0xFF
            ):

                code_position += 1

            if code_position >= len(data):

                raise ScrubError(
                    "Truncated marker at "
                    "end of JPEG scan."
                )

            marker = data[
                code_position
            ]

            #
            # FF00 = stuffed literal FF
            # inside entropy-coded data.
            #
            if marker == 0x00:

                raw = data[
                    marker_start:
                    code_position + 1
                ]

                output += raw

                scan_hasher.update(
                    raw
                )

                position = (
                    code_position + 1
                )

                continue

            #
            # Restart markers and TEM are
            # part of the scan stream and
            # are preserved unchanged.
            #
            if (
                marker == 0x01
                or 0xD0
                <= marker
                <= 0xD7
            ):

                raw = data[
                    marker_start:
                    code_position + 1
                ]

                output += raw

                scan_hasher.update(
                    raw
                )

                position = (
                    code_position + 1
                )

                continue

            #
            # We reached a real marker that
            # terminates or interrupts the
            # entropy-coded region.
            #
            in_scan = False

            resume_scan = (
                marker == 0xDC
            )

            position = (
                marker_start
            )

            continue

        marker_start = (
            position
        )

        if (
            data[position]
            != 0xFF
        ):

            raise ScrubError(
                (
                    "Expected JPEG marker "
                    f"at offset 0x"
                    f"{position:08X}."
                )
            )

        code_position = (
            position
        )

        while (
            code_position
            < len(data)
            and data[
                code_position
            ] == 0xFF
        ):

            code_position += 1

        if (
            code_position
            >= len(data)
        ):

            raise ScrubError(
                "Truncated JPEG marker."
            )

        marker = data[
            code_position
        ]

        if marker == 0x00:

            raise ScrubError(
                (
                    "Found FF00 outside "
                    "entropy-coded data at "
                    f"offset 0x"
                    f"{marker_start:08X}."
                )
            )

        marker_end = (
            code_position + 1
        )

        if (
            marker
            in STANDALONE_MARKERS
        ):

            raw = data[
                marker_start:
                marker_end
            ]

            output += raw

            position = (
                marker_end
            )

            if marker == 0xD9:

                saw_eoi = True
                break

            continue

        if (
            code_position + 3
            > len(data)
        ):

            raise ScrubError(
                "Truncated JPEG segment "
                "length."
            )

        declared_length = (
            int.from_bytes(
                data[
                    code_position + 1:
                    code_position + 3
                ],
                byteorder="big",
            )
        )

        if declared_length < 2:

            raise ScrubError(
                (
                    "Invalid JPEG segment "
                    f"length "
                    f"{declared_length}."
                )
            )

        segment_end = (
            code_position
            + 1
            + declared_length
        )

        if segment_end > len(data):

            raise ScrubError(
                (
                    "JPEG segment at offset "
                    f"0x{marker_start:08X} "
                    "is truncated."
                )
            )

        payload = data[
            code_position + 3:
            segment_end
        ]

        raw_segment = data[
            marker_start:
            segment_end
        ]

        reason = (
            _metadata_removal_reason(
                marker,
                payload,
            )
        )

        if reason is None:

            output += (
                raw_segment
            )

        else:

            removed.append(
                RemovedSegment(
                    marker=marker,
                    marker_name=(
                        _marker_name(
                            marker
                        )
                    ),
                    offset=(
                        marker_start
                    ),
                    size=len(
                        raw_segment
                    ),
                    reason=reason,
                )
            )

        position = (
            segment_end
        )

        if marker == 0xDA:

            saw_sos = True
            in_scan = True
            resume_scan = False

        elif (
            resume_scan
            and marker == 0xDC
        ):

            in_scan = True
            resume_scan = False

        else:

            resume_scan = False

    if not saw_sos:

        raise ScrubError(
            "JPEG does not contain "
            "a Start Of Scan marker."
        )

    if not saw_eoi:

        raise ScrubError(
            "JPEG does not contain "
            "an End Of Image marker."
        )

    trailing_bytes_removed = (
        len(data)
        - position
    )

    return _RewriteResult(
        data=bytes(
            output
        ),
        removed_segments=tuple(
            removed
        ),
        trailing_bytes_removed=(
            trailing_bytes_removed
        ),
        scan_data_sha256=(
            scan_hasher.hexdigest()
        ),
    )


def _metadata_removal_reason(
    marker: int,
    payload: bytes,
) -> str | None:

    #
    # JPEG comment.
    #
    if marker == 0xFE:

        return (
            "JPEG comment metadata"
        )

    #
    # APP0:
    # preserve standard JFIF/JFXX.
    #
    if marker == 0xE0:

        if (
            payload.startswith(
                b"JFIF\x00"
            )
            or payload.startswith(
                b"JFXX\x00"
            )
        ):

            return None

        return (
            "APP0 application metadata"
        )

    #
    # APP1:
    # EXIF, XMP and other application
    # metadata are removed.
    #
    if marker == 0xE1:

        if payload.startswith(
            b"Exif\x00\x00"
        ):

            return "EXIF metadata"

        if (
            payload.startswith(
                XMP_IDENTIFIER
            )
            or payload.startswith(
                EXTENDED_XMP_IDENTIFIER
            )
        ):

            return "XMP metadata"

        return (
            "APP1 application metadata"
        )

    #
    # APP2:
    # preserve ICC color profiles but
    # remove other APP2 application data.
    #
    if marker == 0xE2:

        if payload.startswith(
            ICC_IDENTIFIER
        ):

            return None

        return (
            "APP2 non-ICC metadata"
        )

    #
    # APP3 through APP13 are removable
    # metadata/application containers.
    #
    if (
        0xE3
        <= marker
        <= 0xED
    ):

        return (
            f"APP"
            f"{marker - 0xE0} "
            "application metadata"
        )

    #
    # APP14:
    # preserve Adobe technical color
    # transform information.
    #
    if marker == 0xEE:

        if payload.startswith(
            b"Adobe"
        ):

            return None

        return (
            "APP14 application metadata"
        )

    #
    # APP15.
    #
    if marker == 0xEF:

        return (
            "APP15 application metadata"
        )

    return None


def _marker_name(
    marker: int,
) -> str:

    if (
        0xE0
        <= marker
        <= 0xEF
    ):

        return (
            f"APP"
            f"{marker - 0xE0}"
        )

    if marker == 0xFE:

        return "COM"

    return (
        f"FF{marker:02X}"
    )


def _has_gps(
    path: Path,
) -> bool:

    try:

        extract_gps_ifd_from_jpeg(
            path
        )

    except GpsIfdExtractorError:

        return False

    return True


def _atomic_write(
    path: Path,
    data: bytes,
) -> None:

    temporary_path: Path | None = None

    try:

        descriptor, temp_name = (
            tempfile.mkstemp(
                prefix=(
                    f".{path.name}."
                ),
                suffix=".tmp",
                dir=path.parent,
            )
        )

        temporary_path = Path(
            temp_name
        )

        with os.fdopen(
            descriptor,
            "wb",
        ) as file:

            file.write(
                data
            )

            file.flush()

            os.fsync(
                file.fileno()
            )

        if path.exists():

            raise ScrubError(
                f"Output file appeared "
                f"during operation: {path}"
            )

        os.replace(
            temporary_path,
            path,
        )

        temporary_path = None

    except OSError as exc:

        raise ScrubError(
            f"Could not write sanitized "
            f"file: {exc}"
        ) from exc

    finally:

        if (
            temporary_path
            is not None
        ):

            temporary_path.unlink(
                missing_ok=True
            )
