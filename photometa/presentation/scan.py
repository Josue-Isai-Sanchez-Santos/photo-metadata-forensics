from __future__ import annotations

from collections.abc import Sequence

from photometa.analysis.comparison import (
    ImageComparisonSnapshot,
)
from photometa.fileinfo import (
    format_file_size,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)


def format_scan_report(
    snapshot: ImageComparisonSnapshot,
) -> str:

    lines = [
        "SCAN",
        "-" * 60,
        f"File:          {snapshot.path}",
        (
            "Size:          "
            f"{format_file_size(snapshot.size_bytes)}"
        ),
        (
            "Resolution:    "
            f"{snapshot.resolution}"
        ),
        (
            "JPEG Process:  "
            f"{snapshot.jpeg_process}"
        ),
        f"SHA256:        {snapshot.sha256}",
        "",
        "METADATA",
        "-" * 60,
        f"EXIF:          {snapshot.exif}",
        f"GPS:           {snapshot.gps}",
        f"XMP:           {snapshot.xmp}",
        f"IPTC:          {snapshot.iptc}",
        f"ICC:           {snapshot.icc}",
        (
            "Camera Model:  "
            f"{snapshot.camera_model or '-'}"
        ),
    ]

    if snapshot.warnings:

        lines.extend(
            (
                "",
                "WARNINGS",
                "-" * 60,
            )
        )

        for warning in (
            snapshot.warnings
        ):

            lines.append(
                f"⚠ {warning}"
            )

    return "\n".join(
        lines
    )


def format_segment_report(
    segments: Sequence[
        JpegSegment
    ],
) -> str:

    lines = [
        "JPEG HEADER SEGMENTS",
        "-" * 72,
        (
            f"{'OFFSET':<12} "
            f"{'MARKER':<8} "
            f"{'TYPE':<10} "
            f"{'LENGTH':<10} "
            "DETAIL"
        ),
        "-" * 72,
    ]

    for segment in segments:

        declared_length = (
            "-"
            if segment.declared_length
            is None
            else str(
                segment.declared_length
            )
        )

        detail = (
            "EXIF"
            if segment.is_exif
            else ""
        )

        lines.append(
            (
                f"0x{segment.offset:08X} "
                f"{segment.marker_hex:<8} "
                f"{segment.name:<10} "
                f"{declared_length:<10} "
                f"{detail}"
            )
        )

    lines.extend(
        (
            "",
            (
                "Note: this segment view uses "
                "the header parser and stops "
                "at the first SOS."
            ),
        )
    )

    return "\n".join(
        lines
    )
