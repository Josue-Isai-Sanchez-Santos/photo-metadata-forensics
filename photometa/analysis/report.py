from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from photometa.analysis.anomalies import (
    AnomalyAnalysisError,
    AnomalyReport,
    analyze_anomalies,
)
from photometa.analysis.comparison import (
    PRESENCE_NO,
    PRESENCE_UNKNOWN,
    ComparisonError,
    ImageComparisonSnapshot,
    inspect_image_for_comparison,
)
from photometa.analysis.privacy import (
    PrivacyReport,
    analyze_privacy,
)
from photometa.analysis.privacy_score import (
    PrivacyExposureScore,
    calculate_privacy_exposure_score,
)
from photometa.extractors.gps_ifd import (
    GpsIfdExtractorError,
    GpsMetadata,
    LocationSummary,
    build_location_summary,
    extract_gps_ifd_from_jpeg,
)
from photometa.fileinfo import (
    FileInfo,
    FileInfoError,
    analyze_file,
)
from photometa.hashing import (
    HashingError,
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


class FullReportError(Exception):
    """Base exception for full report generation."""


@dataclass(frozen=True)
class FullReport:
    path: Path

    file_info: FileInfo

    scan: ImageComparisonSnapshot

    privacy: PrivacyReport

    privacy_score: PrivacyExposureScore

    gps_metadata: GpsMetadata | None

    gps_summary: LocationSummary | None

    gps_error: str | None

    anomalies: AnomalyReport


def build_full_report(
    path: str | Path,
) -> FullReport:

    file_path = Path(
        path
    )

    try:

        file_info = analyze_file(
            file_path
        )

    except (
        FileInfoError,
        HashingError,
        OSError,
    ) as exc:

        raise FullReportError(
            (
                "Could not analyze file "
                f"information: {exc}"
            )
        ) from exc

    try:

        scan = (
            inspect_image_for_comparison(
                file_path
            )
        )

    except ComparisonError as exc:

        raise FullReportError(
            (
                "Could not scan JPEG "
                f"metadata: {exc}"
            )
        ) from exc

    try:

        privacy = analyze_privacy(
            file_path
        )

    except (
        JpegParserError,
        XmpParserError,
        IptcParserError,
        OSError,
    ) as exc:

        raise FullReportError(
            (
                "Could not complete "
                f"privacy analysis: {exc}"
            )
        ) from exc

    privacy_score = (
        calculate_privacy_exposure_score(
            privacy
        )
    )

    try:

        anomalies = analyze_anomalies(
            file_path
        )

    except AnomalyAnalysisError as exc:

        raise FullReportError(
            (
                "Could not complete "
                f"anomaly analysis: {exc}"
            )
        ) from exc

    gps_metadata: (
        GpsMetadata
        | None
    ) = None

    gps_summary: (
        LocationSummary
        | None
    ) = None

    gps_error: (
        str
        | None
    ) = None

    if scan.gps == PRESENCE_UNKNOWN:

        gps_error = (
            "GPS status could not be "
            "determined because EXIF "
            "could not be fully parsed."
        )

    elif scan.gps != PRESENCE_NO:

        try:

            gps_metadata = (
                extract_gps_ifd_from_jpeg(
                    file_path
                )
            )

            gps_summary = (
                build_location_summary(
                    gps_metadata
                )
            )

        except GpsIfdExtractorError as exc:

            gps_error = str(
                exc
            )

    return FullReport(
        path=file_info.path,
        file_info=file_info,
        scan=scan,
        privacy=privacy,
        privacy_score=(
            privacy_score
        ),
        gps_metadata=(
            gps_metadata
        ),
        gps_summary=(
            gps_summary
        ),
        gps_error=gps_error,
        anomalies=anomalies,
    )
