from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from photometa.fileinfo import (
    FileInfoError,
    get_jpeg_dimensions,
)
from photometa.hashing import (
    HashingError,
    calculate_sha256,
)
from photometa.parsers.exif import (
    EXIF_IDENTIFIER,
    ExifParserError,
    parse_exif,
)
from photometa.parsers.icc import (
    ICC_IDENTIFIER,
)
from photometa.parsers.iptc import (
    PHOTOSHOP_IDENTIFIER,
    IptcParserError,
    extract_iptc_resource,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)
from photometa.parsers.tiff import (
    TiffParserError,
    decode_ifd_value,
)
from photometa.parsers.xmp import (
    EXTENDED_XMP_IDENTIFIER,
    XMP_IDENTIFIER,
)
from photometa.sanitization.jpeg_rewriter import (
    JpegRewriteError,
    SegmentTransform,
    rewrite_jpeg_bytes,
)


class ComparisonError(Exception):
    """Base exception for image comparison errors."""


PRESENCE_YES = "YES"
PRESENCE_NO = "NO"
PRESENCE_UNKNOWN = "UNKNOWN"

RECOMPRESSION_NONE = "NO EVIDENCE"
RECOMPRESSION_POSSIBLE = "POSSIBLE"
RECOMPRESSION_LIKELY = "LIKELY"

GPS_IFD_POINTER_TAG = 0x8825
CAMERA_MODEL_TAG = 0x0110

JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


@dataclass(frozen=True)
class ImageComparisonSnapshot:
    path: Path

    size_bytes: int
    sha256: str

    width: int
    height: int

    exif: str
    gps: str
    xmp: str
    icc: str
    iptc: str

    camera_model: str | None

    jpeg_process: str

    scan_data_sha256: str

    quantization_fingerprint: str | None
    huffman_fingerprint: str | None

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


@dataclass(frozen=True)
class ComparisonChange:
    code: str
    message: str


@dataclass(frozen=True)
class RecompressionAssessment:
    level: str
    message: str

    evidence: tuple[
        str,
        ...
    ]


@dataclass(frozen=True)
class ImageComparisonReport:
    original: ImageComparisonSnapshot
    copy: ImageComparisonSnapshot

    changes: tuple[
        ComparisonChange,
        ...
    ]

    recompression: RecompressionAssessment

    @property
    def identical_files(
        self,
    ) -> bool:

        return (
            self.original.sha256
            == self.copy.sha256
        )

    def has_change(
        self,
        code: str,
    ) -> bool:

        return any(
            change.code == code
            for change
            in self.changes
        )


def compare_images(
    original: str | Path,
    copy: str | Path,
) -> ImageComparisonReport:

    original_snapshot = (
        inspect_image_for_comparison(
            original
        )
    )

    copy_snapshot = (
        inspect_image_for_comparison(
            copy
        )
    )

    changes = _detect_changes(
        original_snapshot,
        copy_snapshot,
    )

    recompression = (
        _assess_recompression(
            original_snapshot,
            copy_snapshot,
        )
    )

    return ImageComparisonReport(
        original=original_snapshot,
        copy=copy_snapshot,
        changes=tuple(
            changes
        ),
        recompression=recompression,
    )


def inspect_image_for_comparison(
    path: str | Path,
) -> ImageComparisonSnapshot:

    image_path = Path(
        path
    )

    if not image_path.exists():

        raise ComparisonError(
            f"File does not exist: "
            f"{image_path}"
        )

    if not image_path.is_file():

        raise ComparisonError(
            f"Path is not a file: "
            f"{image_path}"
        )

    try:

        width, height = (
            get_jpeg_dimensions(
                image_path
            )
        )

    except FileInfoError as exc:

        raise ComparisonError(
            f"JPEG validation failed for "
            f"{image_path}: {exc}"
        ) from exc

    try:

        sha256 = calculate_sha256(
            image_path
        )

    except HashingError as exc:

        raise ComparisonError(
            f"Could not hash "
            f"{image_path}: {exc}"
        ) from exc

    try:

        data = image_path.read_bytes()

    except OSError as exc:

        raise ComparisonError(
            f"Could not read "
            f"{image_path}: {exc}"
        ) from exc

    exif = PRESENCE_NO
    gps = PRESENCE_NO
    xmp = PRESENCE_NO
    icc = PRESENCE_NO
    iptc = PRESENCE_NO

    camera_model: str | None = None

    warnings: list[str] = []

    dqt_payloads: list[
        bytes
    ] = []

    dht_payloads: list[
        bytes
    ] = []

    sof_markers: list[
        int
    ] = []

    def collector(
        marker: int,
        payload: bytes,
    ) -> SegmentTransform:

        nonlocal exif
        nonlocal gps
        nonlocal xmp
        nonlocal icc
        nonlocal iptc
        nonlocal camera_model

        if marker == 0xDB:

            dqt_payloads.append(
                payload
            )

        if marker == 0xC4:

            dht_payloads.append(
                payload
            )

        if (
            marker
            in JPEG_SOF_MARKERS
        ):

            sof_markers.append(
                marker
            )

        if (
            marker == 0xE1
            and payload.startswith(
                EXIF_IDENTIFIER
            )
        ):

            exif = PRESENCE_YES

            segment = JpegSegment(
                offset=0,
                marker=0xE1,
                name="APP1",
                declared_length=(
                    len(payload) + 2
                ),
                payload_length=len(
                    payload
                ),
                is_exif=True,
                payload=payload,
            )

            try:

                parsed = parse_exif(
                    segment
                )

                gps = (
                    PRESENCE_YES
                    if any(
                        entry.tag
                        == GPS_IFD_POINTER_TAG
                        for entry
                        in parsed.ifd0.entries
                    )
                    else PRESENCE_NO
                )

                model_entry = next(
                    (
                        entry
                        for entry
                        in parsed.ifd0.entries
                        if entry.tag
                        == CAMERA_MODEL_TAG
                    ),
                    None,
                )

                if (
                    model_entry
                    is not None
                ):

                    value = (
                        decode_ifd_value(
                            parsed.tiff_data,
                            model_entry,
                            parsed.header.byte_order,
                        )
                    )

                    if isinstance(
                        value,
                        str,
                    ):

                        value = (
                            value.strip()
                        )

                        if value:

                            camera_model = (
                                value
                            )

            except (
                ExifParserError,
                TiffParserError,
            ) as exc:

                gps = (
                    PRESENCE_UNKNOWN
                )

                warnings.append(
                    (
                        "EXIF present but "
                        "could not be fully "
                        f"parsed: {exc}"
                    )
                )

        if (
            marker == 0xE1
            and (
                payload.startswith(
                    XMP_IDENTIFIER
                )
                or payload.startswith(
                    EXTENDED_XMP_IDENTIFIER
                )
            )
        ):

            xmp = PRESENCE_YES

        if (
            marker == 0xE2
            and payload.startswith(
                ICC_IDENTIFIER
            )
        ):

            icc = PRESENCE_YES

        if (
            marker == 0xED
            and payload.startswith(
                PHOTOSHOP_IDENTIFIER
            )
        ):

            segment = JpegSegment(
                offset=0,
                marker=0xED,
                name="APP13",
                declared_length=(
                    len(payload) + 2
                ),
                payload_length=len(
                    payload
                ),
                is_exif=False,
                payload=payload,
            )

            try:

                resource = (
                    extract_iptc_resource(
                        segment
                    )
                )

                if resource is not None:

                    iptc = PRESENCE_YES

            except IptcParserError as exc:

                if (
                    iptc
                    != PRESENCE_YES
                ):

                    iptc = (
                        PRESENCE_UNKNOWN
                    )

                warnings.append(
                    (
                        "Photoshop APP13 "
                        "present but IPTC "
                        "could not be fully "
                        f"parsed: {exc}"
                    )
                )

        return (
            SegmentTransform
            .preserve(
                payload
            )
        )

    try:

        jpeg_result = (
            rewrite_jpeg_bytes(
                data,
                collector,
                strip_trailing=False,
            )
        )

    except JpegRewriteError as exc:

        raise ComparisonError(
            f"Could not inspect complete "
            f"JPEG {image_path}: {exc}"
        ) from exc

    return ImageComparisonSnapshot(
        path=image_path.resolve(),
        size_bytes=len(
            data
        ),
        sha256=sha256,
        width=width,
        height=height,
        exif=exif,
        gps=gps,
        xmp=xmp,
        icc=icc,
        iptc=iptc,
        camera_model=(
            camera_model
        ),
        jpeg_process=(
            _jpeg_process(
                sof_markers
            )
        ),
        scan_data_sha256=(
            jpeg_result
            .scan_data_sha256
        ),
        quantization_fingerprint=(
            _payload_fingerprint(
                dqt_payloads
            )
        ),
        huffman_fingerprint=(
            _payload_fingerprint(
                dht_payloads
            )
        ),
        warnings=tuple(
            warnings
        ),
    )


def _detect_changes(
    original: ImageComparisonSnapshot,
    copy: ImageComparisonSnapshot,
) -> list[
    ComparisonChange
]:

    changes: list[
        ComparisonChange
    ] = []

    _compare_presence(
        changes,
        code="exif",
        label="EXIF metadata",
        original=original.exif,
        copy=copy.exif,
    )

    _compare_presence(
        changes,
        code="gps",
        label="GPS metadata",
        original=original.gps,
        copy=copy.gps,
    )

    _compare_presence(
        changes,
        code="xmp",
        label="XMP metadata",
        original=original.xmp,
        copy=copy.xmp,
    )

    _compare_presence(
        changes,
        code="iptc",
        label="IPTC metadata",
        original=original.iptc,
        copy=copy.iptc,
    )

    _compare_presence(
        changes,
        code="icc",
        label="ICC profile",
        original=original.icc,
        copy=copy.icc,
    )

    if (
        original.camera_model
        and not copy.camera_model
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "camera_model_removed"
                ),
                message=(
                    "Camera model "
                    "metadata removed"
                ),
            )
        )

    elif (
        not original.camera_model
        and copy.camera_model
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "camera_model_added"
                ),
                message=(
                    "Camera model "
                    "metadata added"
                ),
            )
        )

    elif (
        original.camera_model
        != copy.camera_model
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "camera_model_changed"
                ),
                message=(
                    "Camera model "
                    "metadata changed"
                ),
            )
        )

    if (
        original.width
        != copy.width
        or original.height
        != copy.height
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "resolution_changed"
                ),
                message=(
                    "Resolution changed"
                ),
            )
        )

    if (
        original.jpeg_process
        != copy.jpeg_process
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "jpeg_process_changed"
                ),
                message=(
                    "JPEG coding process "
                    "changed"
                ),
            )
        )

    if (
        _known_fingerprints_differ(
            original
            .quantization_fingerprint,
            copy
            .quantization_fingerprint,
        )
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "quantization_changed"
                ),
                message=(
                    "JPEG quantization "
                    "tables changed"
                ),
            )
        )

    if (
        _known_fingerprints_differ(
            original
            .huffman_fingerprint,
            copy
            .huffman_fingerprint,
        )
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "huffman_changed"
                ),
                message=(
                    "JPEG Huffman tables "
                    "changed"
                ),
            )
        )

    if (
        original.scan_data_sha256
        != copy.scan_data_sha256
    ):

        changes.append(
            ComparisonChange(
                code=(
                    "compressed_data_changed"
                ),
                message=(
                    "Compressed JPEG image "
                    "data changed"
                ),
            )
        )

    return changes


def _compare_presence(
    changes: list[
        ComparisonChange
    ],
    *,
    code: str,
    label: str,
    original: str,
    copy: str,
) -> None:

    if (
        original == PRESENCE_YES
        and copy == PRESENCE_NO
    ):

        changes.append(
            ComparisonChange(
                code=(
                    f"{code}_removed"
                ),
                message=(
                    f"{label} removed"
                ),
            )
        )

    elif (
        original == PRESENCE_NO
        and copy == PRESENCE_YES
    ):

        changes.append(
            ComparisonChange(
                code=(
                    f"{code}_added"
                ),
                message=(
                    f"{label} added"
                ),
            )
        )


def _assess_recompression(
    original: ImageComparisonSnapshot,
    copy: ImageComparisonSnapshot,
) -> RecompressionAssessment:

    if (
        original.sha256
        == copy.sha256
    ):

        return RecompressionAssessment(
            level=(
                RECOMPRESSION_NONE
            ),
            message=(
                "Files are byte-for-byte "
                "identical."
            ),
            evidence=(),
        )

    scan_changed = (
        original.scan_data_sha256
        != copy.scan_data_sha256
    )

    resolution_changed = (
        original.width
        != copy.width
        or original.height
        != copy.height
    )

    quantization_changed = (
        _known_fingerprints_differ(
            original
            .quantization_fingerprint,
            copy
            .quantization_fingerprint,
        )
    )

    huffman_changed = (
        _known_fingerprints_differ(
            original
            .huffman_fingerprint,
            copy
            .huffman_fingerprint,
        )
    )

    process_changed = (
        original.jpeg_process
        != copy.jpeg_process
    )

    evidence: list[str] = []

    if scan_changed:

        evidence.append(
            "compressed JPEG image "
            "data differs"
        )

    if resolution_changed:

        evidence.append(
            "resolution differs"
        )

    if quantization_changed:

        evidence.append(
            "quantization tables differ"
        )

    if huffman_changed:

        evidence.append(
            "Huffman tables differ"
        )

    if process_changed:

        evidence.append(
            "JPEG coding process differs"
        )

    if (
        scan_changed
        and (
            resolution_changed
            or quantization_changed
            or process_changed
        )
    ):

        return RecompressionAssessment(
            level=(
                RECOMPRESSION_LIKELY
            ),
            message=(
                "JPEG appears to have been "
                "recompressed or re-encoded "
                "(heuristic)."
            ),
            evidence=tuple(
                evidence
            ),
        )

    if (
        scan_changed
        or quantization_changed
        or huffman_changed
        or process_changed
    ):

        return RecompressionAssessment(
            level=(
                RECOMPRESSION_POSSIBLE
            ),
            message=(
                "JPEG coding data changed; "
                "recompression or pixel "
                "modification is possible "
                "(heuristic)."
            ),
            evidence=tuple(
                evidence
            ),
        )

    return RecompressionAssessment(
        level=(
            RECOMPRESSION_NONE
        ),
        message=(
            "No JPEG re-encoding evidence "
            "detected by the supported "
            "heuristics."
        ),
        evidence=(),
    )


def _payload_fingerprint(
    payloads: list[
        bytes
    ],
) -> str | None:

    if not payloads:

        return None

    digest = hashlib.sha256()

    for payload in payloads:

        digest.update(
            len(payload).to_bytes(
                4,
                "big",
            )
        )

        digest.update(
            payload
        )

    return digest.hexdigest()


def _known_fingerprints_differ(
    original: str | None,
    copy: str | None,
) -> bool:

    return (
        original is not None
        and copy is not None
        and original != copy
    )


def _jpeg_process(
    markers: list[int],
) -> str:

    if not markers:

        return "UNKNOWN"

    marker = markers[0]

    names = {
        0xC0: "Baseline DCT",
        0xC1: "Extended sequential DCT",
        0xC2: "Progressive DCT",
        0xC3: "Lossless sequential",
        0xC5: "Differential sequential DCT",
        0xC6: "Differential progressive DCT",
        0xC7: "Differential lossless",
        0xC9: "Arithmetic sequential DCT",
        0xCA: "Arithmetic progressive DCT",
        0xCB: "Arithmetic lossless",
        0xCD: "Differential arithmetic sequential",
        0xCE: "Differential arithmetic progressive",
        0xCF: "Differential arithmetic lossless",
    }

    return names.get(
        marker,
        f"SOF 0x{marker:02X}",
    )
