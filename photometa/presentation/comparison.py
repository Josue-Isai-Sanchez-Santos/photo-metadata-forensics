from __future__ import annotations

from photometa.analysis.comparison import (
    ImageComparisonReport,
)
from photometa.fileinfo import (
    format_file_size,
)

LABEL_WIDTH = 22
VALUE_WIDTH = 28


def format_comparison_report(
    report: ImageComparisonReport,
) -> str:

    original = report.original
    copy = report.copy

    lines = [
        "METADATA COMPARISON",
        "-" * 78,
        (
            f"Original: "
            f"{original.path}"
        ),
        (
            f"Copy:     "
            f"{copy.path}"
        ),
        "",
        _row(
            "",
            "ORIGINAL",
            "COPY",
        ),
        _row(
            "EXIF",
            original.exif,
            copy.exif,
        ),
        _row(
            "GPS",
            original.gps,
            copy.gps,
        ),
        _row(
            "XMP",
            original.xmp,
            copy.xmp,
        ),
        _row(
            "IPTC",
            original.iptc,
            copy.iptc,
        ),
        _row(
            "ICC",
            original.icc,
            copy.icc,
        ),
        _row(
            "Camera Model",
            (
                original.camera_model
                or "-"
            ),
            (
                copy.camera_model
                or "-"
            ),
        ),
        _row(
            "Resolution",
            original.resolution,
            copy.resolution,
        ),
        _row(
            "File Size",
            format_file_size(
                original.size_bytes
            ),
            format_file_size(
                copy.size_bytes
            ),
        ),
        _row(
            "JPEG Process",
            original.jpeg_process,
            copy.jpeg_process,
        ),
        "",
        "Changes detected:",
        "",
    ]

    if report.changes:

        for change in (
            report.changes
        ):

            lines.append(
                f"- {change.message}"
            )

    else:

        lines.append(
            "- No supported differences "
            "detected"
        )

    lines.extend(
        (
            "",
            (
                "Recompression assessment: "
                f"{report.recompression.level}"
            ),
            (
                report.recompression.message
            ),
        )
    )

    if (
        report.recompression.evidence
    ):

        lines.append(
            "Evidence:"
        )

        for evidence in (
            report.recompression.evidence
        ):

            lines.append(
                f"- {evidence}"
            )

    warnings = (
        original.warnings
        + copy.warnings
    )

    if warnings:

        lines.extend(
            (
                "",
                "Warnings:",
            )
        )

        for warning in warnings:

            lines.append(
                f"- {warning}"
            )

    lines.extend(
        (
            "",
            (
                "Note: recompression detection "
                "is heuristic. It does not "
                "prove provenance, editing, "
                "or that COPY derives from "
                "ORIGINAL."
            ),
        )
    )

    return "\n".join(
        lines
    )


def _row(
    label: str,
    original: object,
    copy: object,
) -> str:

    return (
        f"{label:<{LABEL_WIDTH}}"
        f"{_fit(original):<{VALUE_WIDTH}}"
        f"{_fit(copy):<{VALUE_WIDTH}}"
    )


def _fit(
    value: object,
) -> str:

    text = str(
        value
    )

    maximum = (
        VALUE_WIDTH - 1
    )

    if len(text) <= maximum:

        return text

    return (
        text[
            :maximum - 1
        ]
        + "…"
    )
