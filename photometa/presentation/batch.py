from __future__ import annotations

from photometa.analysis.batch import (
    FORMAT_JPEG,
    BatchFileResult,
    BatchReport,
)


def format_batch_scan_report(
    report: BatchReport,
) -> str:

    lines = [
        "BATCH SCAN",
        "-" * 60,
        (
            "Directory: "
            f"{report.root}"
        ),
        (
            "Recursive: "
            + (
                "YES"
                if report.recursive
                else "NO"
            )
        ),
        "",
        (
            f"Scanning "
            f"{report.total_files} "
            f"{_plural(report.total_files, 'file')}..."
        ),
        "",
        (
            f"{report.jpeg_count:>5} "
            "JPEG"
        ),
        (
            f"{report.png_count:>5} "
            "PNG "
            "(recognized, not analyzed)"
        ),
        (
            f"{report.unsupported_count:>5} "
            "unsupported"
        ),
        "",
        (
            "JPEG analyzed:          "
            f"{report.analyzed_jpeg_count}"
        ),
        (
            "JPEG failed:            "
            f"{report.failed_jpeg_count}"
        ),
        (
            "GPS metadata detected:  "
            f"{report.gps_detected_count}"
        ),
        "",
        "Privacy exposure:",
        (
            "HIGH:                   "
            f"{report.high_privacy_count}"
        ),
        (
            "MEDIUM:                 "
            f"{report.medium_privacy_count}"
        ),
        (
            "LOW:                    "
            f"{report.low_privacy_count}"
        ),
    ]

    failures = _jpeg_failures(
        report
    )

    if failures:

        lines.extend(
            (
                "",
                "FAILED JPEG",
                "-" * 60,
            )
        )

        for item in failures:

            lines.append(
                (
                    f"- {_relative_path(report, item)}"
                    f": {item.error}"
                )
            )

    return "\n".join(
        lines
    )


def format_batch_privacy_report(
    report: BatchReport,
    *,
    detailed: bool = False,
) -> str:

    lines = [
        "BATCH PRIVACY ANALYSIS",
        "-" * 60,
        (
            "Directory: "
            f"{report.root}"
        ),
        (
            "Recursive: "
            + (
                "YES"
                if report.recursive
                else "NO"
            )
        ),
        "",
        (
            f"Scanning "
            f"{report.total_files} "
            f"{_plural(report.total_files, 'file')}..."
        ),
        "",
        (
            f"JPEG:                   "
            f"{report.jpeg_count}"
        ),
        (
            f"PNG:                    "
            f"{report.png_count} "
            "(recognized, not analyzed)"
        ),
        (
            f"Unsupported:            "
            f"{report.unsupported_count}"
        ),
        (
            f"JPEG analyzed:          "
            f"{report.analyzed_jpeg_count}"
        ),
        (
            f"JPEG failed:            "
            f"{report.failed_jpeg_count}"
        ),
        "",
        (
            "GPS metadata detected:  "
            f"{report.gps_detected_count}"
        ),
        "",
        "PRIVACY EXPOSURE",
        "-" * 60,
        (
            "HIGH:                   "
            f"{report.high_privacy_count}"
        ),
        (
            "MEDIUM:                 "
            f"{report.medium_privacy_count}"
        ),
        (
            "LOW:                    "
            f"{report.low_privacy_count}"
        ),
        "",
        (
            "Exposure levels are based "
            "on PhotoMeta's rule-based "
            "metadata exposure score."
        ),
        (
            "They are not probabilities "
            "of harm, compromise, tracking, "
            "or identification."
        ),
    ]

    if detailed:

        lines.extend(
            (
                "",
                "JPEG RESULTS",
                "-" * 60,
            )
        )

        jpeg_items = (
            item
            for item
            in report.items
            if item.detected_format
            == FORMAT_JPEG
        )

        for item in jpeg_items:

            relative = (
                _relative_path(
                    report,
                    item,
                )
            )

            if item.error is not None:

                lines.append(
                    (
                        f"[ERROR] {relative}"
                        f" — {item.error}"
                    )
                )

                continue

            gps = (
                "YES"
                if item.gps_detected
                else "NO"
            )

            lines.append(
                (
                    f"[{item.privacy_level}] "
                    f"{item.privacy_points}/100 "
                    f"GPS={gps} "
                    f"{relative}"
                )
            )

    return "\n".join(
        lines
    )


def _jpeg_failures(
    report: BatchReport,
) -> tuple[
    BatchFileResult,
    ...
]:

    return tuple(
        item
        for item
        in report.items
        if (
            item.detected_format
            == FORMAT_JPEG
            and item.error is not None
        )
    )


def _relative_path(
    report: BatchReport,
    item: BatchFileResult,
) -> str:

    try:

        return str(
            item.path.relative_to(
                report.root
            )
        )

    except ValueError:

        return str(
            item.path
        )


def _plural(
    count: int,
    singular: str,
) -> str:

    if count == 1:

        return singular

    return (
        singular
        + "s"
    )
