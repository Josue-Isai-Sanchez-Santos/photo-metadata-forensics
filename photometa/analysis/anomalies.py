from __future__ import annotations

from collections import Counter
from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from pathlib import Path
from typing import Mapping

from photometa.fileinfo import (
    FileInfoError,
    get_jpeg_dimensions,
)
from photometa.parsers.exif import (
    EXIF_IDENTIFIER,
    ExifData,
    ExifParserError,
    parse_exif,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)
from photometa.parsers.tags import (
    get_exif_tag_name,
    get_gps_tag_name,
    get_tiff_tag_name,
)
from photometa.parsers.tiff import (
    Ifd,
    IfdEntry,
    TiffParserError,
    decode_ifd_value,
    get_ifd_entry_data_size,
    parse_ifd,
)
from photometa.sanitization.jpeg_rewriter import (
    JpegRewriteError,
    SegmentTransform,
    rewrite_jpeg_bytes,
)


class AnomalyAnalysisError(Exception):
    """Base exception for anomaly analysis errors."""


SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

CATEGORY_STRUCTURAL = "structural"
CATEGORY_CONSISTENCY = "consistency"
CATEGORY_HEURISTIC = "heuristic"


EXIF_IFD_POINTER_TAG = 0x8769
GPS_IFD_POINTER_TAG = 0x8825


IFD0_SELECTED_TAGS = {
    0x0100: "ImageWidth",
    0x0101: "ImageLength",
    0x010F: "Make",
    0x0110: "Model",
    0x0131: "Software",
    0x0132: "DateTime",
}

EXIF_SELECTED_TAGS = {
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",
    0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",
}

GPS_SELECTED_TAGS = {
    0x0001: "GPSLatitudeRef",
    0x0002: "GPSLatitude",
    0x0003: "GPSLongitudeRef",
    0x0004: "GPSLongitude",
    0x0007: "GPSTimeStamp",
    0x001D: "GPSDateStamp",
}


KNOWN_EDITING_SOFTWARE = (
    "adobe",
    "photoshop",
    "lightroom",
    "gimp",
    "snapseed",
    "imagemagick",
    "pillow",
    "affinity",
    "capture one",
    "darktable",
    "luminar",
    "paint.net",
    "canva",
)


@dataclass(frozen=True)
class AnomalyFinding:
    code: str
    severity: str
    category: str
    message: str

    evidence: tuple[
        str,
        ...
    ] = ()


@dataclass(frozen=True)
class AnomalyContext:
    jpeg_width: int
    jpeg_height: int

    ifd0: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )

    exif: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )

    gps: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )

    exif_segment_count: int = 0

    structural_findings: tuple[
        AnomalyFinding,
        ...
    ] = ()


@dataclass(frozen=True)
class AnomalyReport:
    path: Path | None

    findings: tuple[
        AnomalyFinding,
        ...
    ]

    @property
    def has_findings(
        self,
    ) -> bool:

        return bool(
            self.findings
        )

    @property
    def count(
        self,
    ) -> int:

        return len(
            self.findings
        )

    def has(
        self,
        code: str,
    ) -> bool:

        return any(
            finding.code == code
            for finding
            in self.findings
        )


def analyze_anomalies(
    path: str | Path,
) -> AnomalyReport:
    """
    Analyze metadata and JPEG structure
    for inconsistencies.

    A finding is evidence worth reviewing.
    It is NOT proof of image manipulation,
    forgery, editing, or provenance.
    """

    image_path = Path(
        path
    )

    if not image_path.exists():

        raise AnomalyAnalysisError(
            f"File does not exist: "
            f"{image_path}"
        )

    if not image_path.is_file():

        raise AnomalyAnalysisError(
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

        raise AnomalyAnalysisError(
            f"JPEG validation failed: "
            f"{exc}"
        ) from exc

    try:

        data = image_path.read_bytes()

    except OSError as exc:

        raise AnomalyAnalysisError(
            f"Could not read file: "
            f"{exc}"
        ) from exc

    structural_findings: list[
        AnomalyFinding
    ] = []

    ifd0_values: dict[
        str,
        object,
    ] = {}

    exif_values: dict[
        str,
        object,
    ] = {}

    gps_values: dict[
        str,
        object,
    ] = {}

    exif_segment_count = 0
    semantic_exif_captured = False

    def collector(
        marker: int,
        payload: bytes,
    ) -> SegmentTransform:

        nonlocal exif_segment_count
        nonlocal semantic_exif_captured
        nonlocal ifd0_values
        nonlocal exif_values
        nonlocal gps_values

        if (
            marker == 0xE1
            and payload.startswith(
                EXIF_IDENTIFIER
            )
        ):

            exif_segment_count += 1

            segment = JpegSegment(
                offset=0,
                marker=0xE1,
                name="APP1",
                declared_length=(
                    len(payload)
                    + 2
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

            except ExifParserError as exc:

                structural_findings.append(
                    AnomalyFinding(
                        code=(
                            "exif_structure_corrupt"
                        ),
                        severity=(
                            SEVERITY_HIGH
                        ),
                        category=(
                            CATEGORY_STRUCTURAL
                        ),
                        message=(
                            "EXIF is declared but "
                            "its TIFF structure "
                            "could not be parsed"
                        ),
                        evidence=(
                            str(exc),
                        ),
                    )
                )

                return (
                    SegmentTransform
                    .preserve(
                        payload
                    )
                )

            (
                current_ifd0,
                current_exif,
                current_gps,
                current_findings,
            ) = _inspect_exif_structure(
                parsed
            )

            structural_findings.extend(
                current_findings
            )

            #
            # Semantic rules use the first
            # valid EXIF segment.
            #
            if not semantic_exif_captured:

                ifd0_values = (
                    current_ifd0
                )

                exif_values = (
                    current_exif
                )

                gps_values = (
                    current_gps
                )

                semantic_exif_captured = (
                    True
                )

        return (
            SegmentTransform
            .preserve(
                payload
            )
        )

    try:

        rewrite_jpeg_bytes(
            data,
            collector,
            strip_trailing=False,
        )

    except JpegRewriteError as exc:

        structural_findings.append(
            AnomalyFinding(
                code=(
                    "jpeg_structure_error"
                ),
                severity=SEVERITY_HIGH,
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    "JPEG structure could "
                    "not be fully traversed"
                ),
                evidence=(
                    str(exc),
                ),
            )
        )

    context = AnomalyContext(
        jpeg_width=width,
        jpeg_height=height,
        ifd0=ifd0_values,
        exif=exif_values,
        gps=gps_values,
        exif_segment_count=(
            exif_segment_count
        ),
        structural_findings=tuple(
            structural_findings
        ),
    )

    report = (
        analyze_anomaly_context(
            context
        )
    )

    return AnomalyReport(
        path=image_path.resolve(),
        findings=report.findings,
    )


def analyze_anomaly_context(
    context: AnomalyContext,
) -> AnomalyReport:

    findings: list[
        AnomalyFinding
    ] = list(
        context.structural_findings
    )

    #
    # Multiple EXIF APP1 segments.
    #
    if (
        context.exif_segment_count
        > 1
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    "multiple_exif_segments"
                ),
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    "Multiple EXIF APP1 "
                    "segments are present"
                ),
                evidence=(
                    (
                        "EXIF segments="
                        f"{context.exif_segment_count}"
                    ),
                ),
            )
        )

    #
    # DateTime / DateTimeOriginal.
    #
    datetime_value = (
        context.ifd0.get(
            "DateTime"
        )
    )

    original_value = (
        context.exif.get(
            "DateTimeOriginal"
        )
    )

    (
        datetime_parsed,
        datetime_invalid,
    ) = _parse_exif_datetime(
        datetime_value
    )

    (
        original_parsed,
        original_invalid,
    ) = _parse_exif_datetime(
        original_value
    )

    if datetime_invalid:

        findings.append(
            AnomalyFinding(
                code=(
                    "datetime_format_invalid"
                ),
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    "DateTime uses an "
                    "unexpected EXIF format"
                ),
                evidence=(
                    (
                        "DateTime="
                        f"{datetime_value!r}"
                    ),
                ),
            )
        )

    if original_invalid:

        findings.append(
            AnomalyFinding(
                code=(
                    "datetime_original_format_invalid"
                ),
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    "DateTimeOriginal uses an "
                    "unexpected EXIF format"
                ),
                evidence=(
                    (
                        "DateTimeOriginal="
                        f"{original_value!r}"
                    ),
                ),
            )
        )

    if (
        datetime_parsed is not None
        and original_parsed is not None
        and datetime_parsed
        != original_parsed
    ):

        if (
            original_parsed
            > datetime_parsed
        ):

            findings.append(
                AnomalyFinding(
                    code=(
                        "datetime_order_inconsistent"
                    ),
                    severity=(
                        SEVERITY_MEDIUM
                    ),
                    category=(
                        CATEGORY_CONSISTENCY
                    ),
                    message=(
                        "DateTimeOriginal is "
                        "later than DateTime"
                    ),
                    evidence=(
                        (
                            "DateTime="
                            f"{datetime_value}"
                        ),
                        (
                            "DateTimeOriginal="
                            f"{original_value}"
                        ),
                    ),
                )
            )

        else:

            findings.append(
                AnomalyFinding(
                    code=(
                        "datetime_differs"
                    ),
                    severity=(
                        SEVERITY_LOW
                    ),
                    category=(
                        CATEGORY_CONSISTENCY
                    ),
                    message=(
                        "DateTime differs from "
                        "DateTimeOriginal"
                    ),
                    evidence=(
                        (
                            "DateTime="
                            f"{datetime_value}"
                        ),
                        (
                            "DateTimeOriginal="
                            f"{original_value}"
                        ),
                    ),
                )
            )

    #
    # GPS completeness.
    #
    latitude = context.gps.get(
        "GPSLatitude"
    )

    longitude = context.gps.get(
        "GPSLongitude"
    )

    latitude_ref = context.gps.get(
        "GPSLatitudeRef"
    )

    longitude_ref = context.gps.get(
        "GPSLongitudeRef"
    )

    gps_date = context.gps.get(
        "GPSDateStamp"
    )

    latitude_present = (
        _has_value(
            latitude
        )
    )

    longitude_present = (
        _has_value(
            longitude
        )
    )

    if (
        latitude_present
        != longitude_present
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    "gps_coordinates_incomplete"
                ),
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    "GPS coordinate pair "
                    "is incomplete"
                ),
            )
        )

    if (
        latitude_present
        and longitude_present
        and not _has_value(
            gps_date
        )
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    "gps_datestamp_missing"
                ),
                severity=(
                    SEVERITY_LOW
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    "GPS coordinates are "
                    "present without "
                    "GPSDateStamp"
                ),
            )
        )

    missing_references: list[
        str
    ] = []

    if (
        latitude_present
        and not _has_value(
            latitude_ref
        )
    ):

        missing_references.append(
            "GPSLatitudeRef"
        )

    if (
        longitude_present
        and not _has_value(
            longitude_ref
        )
    ):

        missing_references.append(
            "GPSLongitudeRef"
        )

    if missing_references:

        findings.append(
            AnomalyFinding(
                code=(
                    "gps_reference_missing"
                ),
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    "GPS coordinate reference "
                    "field is missing"
                ),
                evidence=tuple(
                    missing_references
                ),
            )
        )

    #
    # EXIF pixel dimensions vs JPEG SOF.
    #
    _check_dimensions(
        findings,
        x_value=(
            context.exif.get(
                "PixelXDimension"
            )
        ),
        y_value=(
            context.exif.get(
                "PixelYDimension"
            )
        ),
        jpeg_width=(
            context.jpeg_width
        ),
        jpeg_height=(
            context.jpeg_height
        ),
        code=(
            "exif_dimensions_mismatch"
        ),
        incomplete_code=(
            "exif_dimensions_incomplete"
        ),
        label=(
            "EXIF pixel dimensions"
        ),
    )

    #
    # IFD0 dimensions vs JPEG SOF.
    #
    _check_dimensions(
        findings,
        x_value=(
            context.ifd0.get(
                "ImageWidth"
            )
        ),
        y_value=(
            context.ifd0.get(
                "ImageLength"
            )
        ),
        jpeg_width=(
            context.jpeg_width
        ),
        jpeg_height=(
            context.jpeg_height
        ),
        code=(
            "ifd0_dimensions_mismatch"
        ),
        incomplete_code=(
            "ifd0_dimensions_incomplete"
        ),
        label=(
            "IFD0 image dimensions"
        ),
    )

    #
    # Software heuristic.
    #
    software = context.ifd0.get(
        "Software"
    )

    if isinstance(
        software,
        str,
    ):

        matched = (
            _known_editing_software(
                software
            )
        )

        if matched is not None:

            findings.append(
                AnomalyFinding(
                    code=(
                        "editing_software_present"
                    ),
                    severity=(
                        SEVERITY_LOW
                    ),
                    category=(
                        CATEGORY_HEURISTIC
                    ),
                    message=(
                        "Software metadata "
                        "references a known "
                        "editing or processing "
                        "tool"
                    ),
                    evidence=(
                        (
                            "Software="
                            f"{software}"
                        ),
                        (
                            "Matched keyword="
                            f"{matched}"
                        ),
                    ),
                )
            )

    #
    # We do NOT guess vendor compatibility.
    # Only detect an incomplete Make/Model
    # pair.
    #
    make = context.ifd0.get(
        "Make"
    )

    model = context.ifd0.get(
        "Model"
    )

    make_present = _has_value(
        make
    )

    model_present = _has_value(
        model
    )

    if (
        make_present
        != model_present
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    "make_model_incomplete"
                ),
                severity=(
                    SEVERITY_LOW
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    "Camera Make/Model pair "
                    "is incomplete"
                ),
                evidence=(
                    (
                        "Make="
                        f"{make!r}"
                    ),
                    (
                        "Model="
                        f"{model!r}"
                    ),
                ),
            )
        )

    findings.sort(
        key=_finding_sort_key
    )

    return AnomalyReport(
        path=None,
        findings=tuple(
            findings
        ),
    )


def _inspect_exif_structure(
    exif: ExifData,
) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    list[AnomalyFinding],
]:

    findings: list[
        AnomalyFinding
    ] = []

    _inspect_ifd_structure(
        exif,
        exif.ifd0,
        group="IFD0",
        findings=findings,
    )

    exif_ifd = (
        _parse_child_ifd(
            exif,
            exif.ifd0,
            pointer_tag=(
                EXIF_IFD_POINTER_TAG
            ),
            label="ExifIFD",
            findings=findings,
        )
    )

    gps_ifd = (
        _parse_child_ifd(
            exif,
            exif.ifd0,
            pointer_tag=(
                GPS_IFD_POINTER_TAG
            ),
            label="GPS IFD",
            findings=findings,
        )
    )

    if exif_ifd is not None:

        _inspect_ifd_structure(
            exif,
            exif_ifd,
            group="ExifIFD",
            findings=findings,
        )

    if gps_ifd is not None:

        _inspect_ifd_structure(
            exif,
            gps_ifd,
            group="GPS",
            findings=findings,
        )

    ifd0_values = (
        _decode_selected_values(
            exif,
            exif.ifd0,
            IFD0_SELECTED_TAGS,
            group="IFD0",
            findings=findings,
        )
    )

    exif_values: dict[
        str,
        object,
    ] = {}

    gps_values: dict[
        str,
        object,
    ] = {}

    if exif_ifd is not None:

        exif_values = (
            _decode_selected_values(
                exif,
                exif_ifd,
                EXIF_SELECTED_TAGS,
                group="ExifIFD",
                findings=findings,
            )
        )

    if gps_ifd is not None:

        gps_values = (
            _decode_selected_values(
                exif,
                gps_ifd,
                GPS_SELECTED_TAGS,
                group="GPS",
                findings=findings,
            )
        )

    return (
        ifd0_values,
        exif_values,
        gps_values,
        findings,
    )


def _parse_child_ifd(
    exif: ExifData,
    parent_ifd: Ifd,
    *,
    pointer_tag: int,
    label: str,
    findings: list[
        AnomalyFinding
    ],
) -> Ifd | None:

    pointer_entry = next(
        (
            entry
            for entry
            in parent_ifd.entries
            if entry.tag
            == pointer_tag
        ),
        None,
    )

    if pointer_entry is None:
        return None

    try:

        value = decode_ifd_value(
            exif.tiff_data,
            pointer_entry,
            exif.header.byte_order,
        )

    except TiffParserError as exc:

        findings.append(
            AnomalyFinding(
                code=(
                    "invalid_ifd_pointer"
                ),
                severity=(
                    SEVERITY_HIGH
                ),
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    f"{label} pointer "
                    "could not be decoded"
                ),
                evidence=(
                    str(exc),
                ),
            )
        )

        return None

    if not isinstance(
        value,
        int,
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    "invalid_ifd_pointer"
                ),
                severity=(
                    SEVERITY_HIGH
                ),
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    f"{label} pointer "
                    "is not an integer offset"
                ),
            )
        )

        return None

    if (
        value < 8
        or value >= len(
            exif.tiff_data
        )
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    "suspicious_offset"
                ),
                severity=(
                    SEVERITY_HIGH
                ),
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    f"{label} pointer is "
                    "outside a safe TIFF "
                    "range"
                ),
                evidence=(
                    f"offset={value}",
                    (
                        "TIFF size="
                        f"{len(exif.tiff_data)}"
                    ),
                ),
            )
        )

        return None

    parent_end = (
        parent_ifd.offset
        + 2
        + (
            len(
                parent_ifd.entries
            )
            * 12
        )
        + 4
    )

    if (
        parent_ifd.offset
        <= value
        < parent_end
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    "suspicious_offset"
                ),
                severity=(
                    SEVERITY_HIGH
                ),
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    f"{label} pointer "
                    "points inside its "
                    "parent IFD directory"
                ),
                evidence=(
                    f"offset={value}",
                ),
            )
        )

        return None

    try:

        return parse_ifd(
            exif.tiff_data,
            value,
            exif.header.byte_order,
        )

    except TiffParserError as exc:

        findings.append(
            AnomalyFinding(
                code=(
                    "invalid_ifd_pointer"
                ),
                severity=(
                    SEVERITY_HIGH
                ),
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    f"{label} structure "
                    "could not be parsed"
                ),
                evidence=(
                    f"offset={value}",
                    str(exc),
                ),
            )
        )

        return None


def _inspect_ifd_structure(
    exif: ExifData,
    ifd: Ifd,
    *,
    group: str,
    findings: list[
        AnomalyFinding
    ],
) -> None:

    #
    # Duplicate tags.
    #
    counts = Counter(
        entry.tag
        for entry
        in ifd.entries
    )

    for tag, count in (
        counts.items()
    ):

        if count <= 1:
            continue

        findings.append(
            AnomalyFinding(
                code="duplicate_tag",
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_STRUCTURAL
                ),
                message=(
                    "Duplicate metadata tag "
                    "detected"
                ),
                evidence=(
                    f"Group={group}",
                    (
                        "Tag="
                        f"{_tag_name(group, tag)}"
                    ),
                    f"Tag ID=0x{tag:04X}",
                    f"Count={count}",
                ),
            )
        )

    directory_start = (
        ifd.offset
    )

    directory_end = (
        ifd.offset
        + 2
        + (
            len(
                ifd.entries
            )
            * 12
        )
        + 4
    )

    for entry in ifd.entries:

        try:

            data_size = (
                get_ifd_entry_data_size(
                    entry
                )
            )

        except TiffParserError as exc:

            findings.append(
                AnomalyFinding(
                    code=(
                        "invalid_tiff_type"
                    ),
                    severity=(
                        SEVERITY_HIGH
                    ),
                    category=(
                        CATEGORY_STRUCTURAL
                    ),
                    message=(
                        "TIFF entry uses an "
                        "unsupported or invalid "
                        "field type"
                    ),
                    evidence=(
                        f"Group={group}",
                        (
                            "Tag="
                            f"{_tag_name(group, entry.tag)}"
                        ),
                        str(exc),
                    ),
                )
            )

            continue

        if data_size <= 4:
            continue

        value_offset = int.from_bytes(
            entry.value_or_offset,
            byteorder=(
                exif.header.byte_order
            ),
        )

        value_end = (
            value_offset
            + data_size
        )

        if value_offset < 8:

            findings.append(
                AnomalyFinding(
                    code=(
                        "suspicious_offset"
                    ),
                    severity=(
                        SEVERITY_HIGH
                    ),
                    category=(
                        CATEGORY_STRUCTURAL
                    ),
                    message=(
                        "External TIFF value "
                        "points inside the "
                        "TIFF header"
                    ),
                    evidence=(
                        f"Group={group}",
                        (
                            "Tag="
                            f"{_tag_name(group, entry.tag)}"
                        ),
                        (
                            "offset="
                            f"{value_offset}"
                        ),
                        (
                            "size="
                            f"{data_size}"
                        ),
                    ),
                )
            )

            continue

        if value_end > len(
            exif.tiff_data
        ):

            findings.append(
                AnomalyFinding(
                    code=(
                        "suspicious_offset"
                    ),
                    severity=(
                        SEVERITY_HIGH
                    ),
                    category=(
                        CATEGORY_STRUCTURAL
                    ),
                    message=(
                        "External TIFF value "
                        "extends beyond the "
                        "EXIF data"
                    ),
                    evidence=(
                        f"Group={group}",
                        (
                            "Tag="
                            f"{_tag_name(group, entry.tag)}"
                        ),
                        (
                            "offset="
                            f"{value_offset}"
                        ),
                        (
                            "size="
                            f"{data_size}"
                        ),
                        (
                            "TIFF size="
                            f"{len(exif.tiff_data)}"
                        ),
                    ),
                )
            )

            continue

        if (
            directory_start
            <= value_offset
            < directory_end
        ):

            findings.append(
                AnomalyFinding(
                    code=(
                        "suspicious_offset"
                    ),
                    severity=(
                        SEVERITY_HIGH
                    ),
                    category=(
                        CATEGORY_STRUCTURAL
                    ),
                    message=(
                        "External TIFF value "
                        "points inside its "
                        "own IFD directory"
                    ),
                    evidence=(
                        f"Group={group}",
                        (
                            "Tag="
                            f"{_tag_name(group, entry.tag)}"
                        ),
                        (
                            "offset="
                            f"{value_offset}"
                        ),
                    ),
                )
            )


def _decode_selected_values(
    exif: ExifData,
    ifd: Ifd,
    selected: Mapping[
        int,
        str,
    ],
    *,
    group: str,
    findings: list[
        AnomalyFinding
    ],
) -> dict[
    str,
    object,
]:

    values: dict[
        str,
        object,
    ] = {}

    for tag, name in (
        selected.items()
    ):

        entry = next(
            (
                current
                for current
                in ifd.entries
                if current.tag
                == tag
            ),
            None,
        )

        if entry is None:
            continue

        try:

            values[name] = (
                decode_ifd_value(
                    exif.tiff_data,
                    entry,
                    exif.header.byte_order,
                )
            )

        except TiffParserError as exc:

            findings.append(
                AnomalyFinding(
                    code=(
                        "tag_value_decode_error"
                    ),
                    severity=(
                        SEVERITY_HIGH
                    ),
                    category=(
                        CATEGORY_STRUCTURAL
                    ),
                    message=(
                        "Metadata tag value "
                        "could not be decoded"
                    ),
                    evidence=(
                        f"Group={group}",
                        f"Tag={name}",
                        str(exc),
                    ),
                )
            )

    return values


def _check_dimensions(
    findings: list[
        AnomalyFinding
    ],
    *,
    x_value: object,
    y_value: object,
    jpeg_width: int,
    jpeg_height: int,
    code: str,
    incomplete_code: str,
    label: str,
) -> None:

    x_present = _has_value(
        x_value
    )

    y_present = _has_value(
        y_value
    )

    if x_present != y_present:

        findings.append(
            AnomalyFinding(
                code=incomplete_code,
                severity=(
                    SEVERITY_LOW
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    f"{label} are incomplete"
                ),
                evidence=(
                    f"X={x_value!r}",
                    f"Y={y_value!r}",
                ),
            )
        )

        return

    if not (
        x_present
        and y_present
    ):

        return

    if not (
        isinstance(
            x_value,
            int,
        )
        and isinstance(
            y_value,
            int,
        )
    ):

        findings.append(
            AnomalyFinding(
                code=(
                    f"{code}_invalid_type"
                ),
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    f"{label} are not "
                    "stored as integer "
                    "dimensions"
                ),
            )
        )

        return

    if (
        x_value != jpeg_width
        or y_value != jpeg_height
    ):

        findings.append(
            AnomalyFinding(
                code=code,
                severity=(
                    SEVERITY_MEDIUM
                ),
                category=(
                    CATEGORY_CONSISTENCY
                ),
                message=(
                    f"{label} do not match "
                    "the JPEG frame"
                ),
                evidence=(
                    (
                        f"Metadata="
                        f"{x_value}x{y_value}"
                    ),
                    (
                        f"JPEG="
                        f"{jpeg_width}x"
                        f"{jpeg_height}"
                    ),
                ),
            )
        )


def _parse_exif_datetime(
    value: object,
) -> tuple[
    datetime | None,
    bool,
]:

    if value is None:

        return (
            None,
            False,
        )

    if not isinstance(
        value,
        str,
    ):

        return (
            None,
            True,
        )

    try:

        parsed = datetime.strptime(
            value,
            "%Y:%m:%d %H:%M:%S",
        )

    except ValueError:

        return (
            None,
            True,
        )

    return (
        parsed,
        False,
    )


def _known_editing_software(
    value: str,
) -> str | None:

    normalized = (
        value.casefold()
    )

    for keyword in (
        KNOWN_EDITING_SOFTWARE
    ):

        if keyword in normalized:

            return keyword

    return None


def _has_value(
    value: object,
) -> bool:

    if value is None:
        return False

    if isinstance(
        value,
        str,
    ):

        return bool(
            value.strip()
        )

    if isinstance(
        value,
        (
            bytes,
            tuple,
            list,
            set,
            dict,
        ),
    ):

        return bool(
            value
        )

    return True


def _tag_name(
    group: str,
    tag: int,
) -> str:

    if group == "ExifIFD":

        return get_exif_tag_name(
            tag
        )

    if group == "GPS":

        return get_gps_tag_name(
            tag
        )

    return get_tiff_tag_name(
        tag
    )


def _finding_sort_key(
    finding: AnomalyFinding,
) -> tuple[
    int,
    str,
    str,
]:

    severity_order = {
        SEVERITY_HIGH: 0,
        SEVERITY_MEDIUM: 1,
        SEVERITY_LOW: 2,
    }

    return (
        severity_order.get(
            finding.severity,
            99,
        ),
        finding.category,
        finding.code,
    )
