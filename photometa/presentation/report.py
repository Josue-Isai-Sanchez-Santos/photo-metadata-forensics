from __future__ import annotations

from photometa.analysis.report import (
    FullReport,
)
from photometa.presentation.anomalies import (
    format_anomaly_detailed_report,
)
from photometa.presentation.fileinfo import (
    format_file_info_report,
)
from photometa.presentation.gps import (
    format_location_report,
)
from photometa.presentation.privacy import (
    format_privacy_detailed_report,
)
from photometa.presentation.privacy_score import (
    format_privacy_score_detailed,
)
from photometa.presentation.scan import (
    format_scan_report,
)


def format_full_report(
    report: FullReport,
    *,
    include_sensitive: bool = False,
) -> str:

    sections = [
        "\n".join(
            (
                "PHOTOMETA REPORT",
                "=" * 60,
                f"File: {report.path}",
            )
        ),
        format_file_info_report(
            report.file_info
        ),
        format_scan_report(
            report.scan
        ),
        format_privacy_detailed_report(
            report.privacy
        ),
        format_privacy_score_detailed(
            report.privacy_score
        ),
        _format_gps_section(
            report,
            include_sensitive=(
                include_sensitive
            ),
        ),
        format_anomaly_detailed_report(
            report.anomalies
        ),
        "\n".join(
            (
                "REPORT NOTES",
                "-" * 60,
                (
                    "This report describes "
                    "supported metadata and "
                    "structural observations."
                ),
                (
                    "It does not establish "
                    "image authenticity, "
                    "provenance, or manipulation."
                ),
            )
        ),
    ]

    return "\n\n".join(
        sections
    )


def _format_gps_section(
    report: FullReport,
    *,
    include_sensitive: bool,
) -> str:

    if report.gps_error is not None:

        return "\n".join(
            (
                "LOCATION",
                "-" * 45,
                "GPS status: ERROR",
                (
                    "Details: "
                    f"{report.gps_error}"
                ),
            )
        )

    if report.gps_summary is None:

        return "\n".join(
            (
                "LOCATION",
                "-" * 45,
                "GPS detected: NO",
            )
        )

    if include_sensitive:

        return format_location_report(
            report.gps_summary
        )

    return "\n".join(
        (
            "LOCATION",
            "-" * 45,
            "GPS detected: YES",
            (
                "Coordinates: hidden in "
                "default report"
            ),
            (
                "Use --include-sensitive "
                "to display GPS values."
            ),
        )
    )
