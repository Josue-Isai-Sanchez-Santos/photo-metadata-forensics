from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from photometa.analysis.batch import (
    BatchReport,
)
from photometa.analysis.comparison import (
    PRESENCE_YES,
    ComparisonError,
    inspect_image_for_comparison,
)
from photometa.analysis.privacy import (
    analyze_privacy,
)
from photometa.analysis.privacy_score import (
    calculate_privacy_exposure_score,
)
from photometa.extractors.exif_ifd import (
    ExifIfdExtractorError,
    build_capture_summary,
    extract_exif_ifd_from_jpeg,
)
from photometa.extractors.gps_ifd import (
    GpsIfdExtractorError,
    build_location_summary,
    extract_gps_ifd_from_jpeg,
)
from photometa.extractors.ifd0 import (
    Ifd0ExtractorError,
    extract_ifd0_from_jpeg,
)
from photometa.parsers.exif import (
    ExifParserError,
)
from photometa.parsers.iptc import (
    IptcParserError,
)
from photometa.parsers.jpeg import (
    JpegParserError,
)
from photometa.parsers.tiff import (
    TiffParserError,
)
from photometa.parsers.xmp import (
    XmpParserError,
)

JSON_SCHEMA_VERSION = "1.0"


class JsonExportError(Exception):
    """Base exception for JSON export errors."""


EXIF_EXTRACTION_ERRORS = (
    Ifd0ExtractorError,
    ExifIfdExtractorError,
    GpsIfdExtractorError,
    ExifParserError,
    TiffParserError,
    JpegParserError,
    OSError,
)


PRIVACY_EXTRACTION_ERRORS = (
    ExifParserError,
    TiffParserError,
    JpegParserError,
    XmpParserError,
    IptcParserError,
    OSError,
)


def build_scan_json_document(
    path: str | Path,
    *,
    include_sensitive: bool = False,
) -> dict[str, Any]:

    file_path = Path(
        path
    )

    try:

        snapshot = (
            inspect_image_for_comparison(
                file_path
            )
        )

    except ComparisonError as exc:

        raise JsonExportError(
            (
                "Could not build JSON "
                f"scan: {exc}"
            )
        ) from exc

    warnings = list(
        snapshot.warnings
    )

    ifd0_values: dict[
        str,
        object,
    ] = {}

    exif_values: dict[
        str,
        object,
    ] = {}

    capture = None

    if snapshot.exif == PRESENCE_YES:

        try:

            ifd0 = (
                extract_ifd0_from_jpeg(
                    file_path
                )
            )

            ifd0_values = (
                ifd0.as_dict()
            )

        except EXIF_EXTRACTION_ERRORS as exc:

            warnings.append(
                (
                    "IFD0 metadata could "
                    f"not be exported: {exc}"
                )
            )

        try:

            exif = (
                extract_exif_ifd_from_jpeg(
                    file_path
                )
            )

            exif_values = (
                exif.as_dict()
            )

            capture = (
                build_capture_summary(
                    exif
                )
            )

        except EXIF_EXTRACTION_ERRORS:

            #
            # ExifIFD is optional.
            # Its absence alone is not
            # necessarily an error.
            #
            capture = None

    gps_payload = (
        _build_gps_payload(
            file_path,
            status=snapshot.gps,
            include_sensitive=(
                include_sensitive
            ),
            warnings=warnings,
        )
    )

    privacy_payload = (
        _build_privacy_payload(
            file_path,
            warnings=warnings,
        )
    )

    return {
        "schema_version": (
            JSON_SCHEMA_VERSION
        ),
        "mode": "single",
        "file": {
            "path": str(
                snapshot.path
            ),
            "name": (
                snapshot.path.name
            ),
            "format": "JPEG",
            "mime_type": (
                "image/jpeg"
            ),
            "size_bytes": (
                snapshot.size_bytes
            ),
            "width": (
                snapshot.width
            ),
            "height": (
                snapshot.height
            ),
            "sha256": (
                snapshot.sha256
            ),
            "jpeg_process": (
                snapshot.jpeg_process
            ),
        },
        "metadata": {
            "exif": snapshot.exif,
            "gps": snapshot.gps,
            "xmp": snapshot.xmp,
            "iptc": snapshot.iptc,
            "icc": snapshot.icc,
        },
        "device": {
            "make": (
                _string_or_none(
                    ifd0_values.get(
                        "Make"
                    )
                )
            ),
            "model": (
                _string_or_none(
                    ifd0_values.get(
                        "Model"
                    )
                )
                or snapshot.camera_model
            ),
            "software": (
                _string_or_none(
                    ifd0_values.get(
                        "Software"
                    )
                )
            ),
        },
        "capture": {
            "datetime_original": (
                _string_or_none(
                    exif_values.get(
                        "DateTimeOriginal"
                    )
                )
            ),
            "date": (
                None
                if capture is None
                else capture.date
            ),
            "time": (
                None
                if capture is None
                else capture.time
            ),
            "exposure": (
                None
                if capture is None
                else capture.exposure
            ),
            "iso": (
                None
                if capture is None
                else capture.iso
            ),
            "aperture": (
                None
                if capture is None
                else capture.aperture
            ),
            "focal_length": (
                None
                if capture is None
                else capture.focal_length
            ),
            "lens": (
                None
                if capture is None
                else capture.lens
            ),
        },
        "gps": gps_payload,
        "privacy": privacy_payload,
        "warnings": warnings,
    }


def build_batch_scan_json_document(
    report: BatchReport,
) -> dict[str, Any]:

    files: list[
        dict[str, Any]
    ] = []

    for item in report.items:

        try:

            relative_path = str(
                item.path.relative_to(
                    report.root
                )
            )

        except ValueError:

            relative_path = str(
                item.path
            )

        privacy: (
            dict[str, Any]
            | None
        ) = None

        if (
            item.privacy_level
            is not None
        ):

            privacy = {
                "level": (
                    item.privacy_level
                ),
                "points": (
                    item.privacy_points
                ),
                "maximum": 100,
            }

        files.append(
            {
                "path": (
                    relative_path
                ),
                "format": (
                    item.detected_format
                ),
                "analyzed": (
                    item.analyzed_successfully
                ),
                "gps_detected": (
                    item.gps_detected
                ),
                "privacy": privacy,
                "error": (
                    item.error
                ),
            }
        )

    return {
        "schema_version": (
            JSON_SCHEMA_VERSION
        ),
        "mode": "batch",
        "directory": str(
            report.root
        ),
        "recursive": (
            report.recursive
        ),
        "summary": {
            "total_files": (
                report.total_files
            ),
            "formats": {
                "jpeg": (
                    report.jpeg_count
                ),
                "png": (
                    report.png_count
                ),
                "webp": (
                    report.webp_count
                ),
                "tiff": (
                    report.tiff_count
                ),
                "heif": (
                    report.heif_count
                ),
                "raw": (
                    report.raw_count
                ),
                "unsupported": (
                    report.unsupported_count
                ),
            },
            "jpeg": {
                "analyzed": (
                    report.analyzed_jpeg_count
                ),
                "failed": (
                    report.failed_jpeg_count
                ),
            },
            "gps_detected": (
                report.gps_detected_count
            ),
            "privacy_exposure": {
                "high": (
                    report.high_privacy_count
                ),
                "medium": (
                    report.medium_privacy_count
                ),
                "low": (
                    report.low_privacy_count
                ),
            },
        },
        "files": files,
    }


def serialize_json_document(
    document: dict[
        str,
        Any,
    ],
) -> str:

    try:

        return json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise JsonExportError(
            (
                "Could not serialize "
                f"JSON document: {exc}"
            )
        ) from exc


def _build_gps_payload(
    path: Path,
    *,
    status: str,
    include_sensitive: bool,
    warnings: list[str],
) -> dict[str, Any]:

    payload: dict[
        str,
        Any,
    ] = {
        "status": status,
        "detected": (
            status == PRESENCE_YES
        ),
        "coordinates_included": (
            False
        ),
        "latitude": None,
        "longitude": None,
        "altitude_m": None,
        "altitude_reference": None,
        "date": None,
        "time": None,
        "image_direction_degrees": (
            None
        ),
        "error": None,
    }

    if status != PRESENCE_YES:

        return payload

    try:

        metadata = (
            extract_gps_ifd_from_jpeg(
                path
            )
        )

        summary = (
            build_location_summary(
                metadata
            )
        )

    except EXIF_EXTRACTION_ERRORS as exc:

        message = (
            "GPS metadata could not "
            f"be normalized: {exc}"
        )

        payload["error"] = (
            str(exc)
        )

        warnings.append(
            message
        )

        return payload

    if not include_sensitive:

        return payload

    payload.update(
        {
            "coordinates_included": (
                True
            ),
            "latitude": (
                summary.latitude
            ),
            "longitude": (
                summary.longitude
            ),
            "altitude_m": (
                summary.altitude
            ),
            "altitude_reference": (
                summary.altitude_reference
            ),
            "date": (
                summary.gps_date
            ),
            "time": (
                summary.gps_time
            ),
            "image_direction_degrees": (
                summary.image_direction
            ),
        }
    )

    return payload


def _build_privacy_payload(
    path: Path,
    *,
    warnings: list[str],
) -> dict[str, Any]:

    try:

        report = analyze_privacy(
            path
        )

        score = (
            calculate_privacy_exposure_score(
                report
            )
        )

    except PRIVACY_EXTRACTION_ERRORS as exc:

        warnings.append(
            (
                "Privacy analysis could "
                f"not be exported: {exc}"
            )
        )

        return {
            "available": False,
            "score": None,
            "findings": [],
            "error": str(
                exc
            ),
        }

    findings = [
        {
            "code": finding.code,
            "severity": (
                finding.severity
            ),
            "message": (
                finding.message
            ),
            "sources": list(
                finding.sources
            ),
            "fields": list(
                finding.fields
            ),
        }
        for finding
        in report.findings
    ]

    return {
        "available": True,
        "score": {
            "level": (
                score.level
            ),
            "points": (
                score.points
            ),
            "maximum": (
                score.maximum
            ),
            "matrix_version": (
                score.version
            ),
        },
        "findings": findings,
        "error": None,
    }


def _string_or_none(
    value: object,
) -> str | None:

    if not isinstance(
        value,
        str,
    ):

        return None

    stripped = (
        value.strip()
    )

    return (
        stripped
        if stripped
        else None
    )
