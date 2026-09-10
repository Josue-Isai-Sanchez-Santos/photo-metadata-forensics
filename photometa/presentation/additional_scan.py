from __future__ import annotations

from photometa.fileinfo import (
    format_file_size,
)
from photometa.formats.pillow_backend import (
    AdditionalImageSnapshot,
)


def format_additional_scan_report(
    snapshot: AdditionalImageSnapshot,
) -> str:

    lines = [
        "SCAN",
        "-" * 60,
        (
            "File:          "
            f"{snapshot.path}"
        ),
        (
            "Format:        "
            f"{snapshot.format}"
        ),
        (
            "MIME type:     "
            f"{snapshot.mime_type}"
        ),
        (
            "Backend:       "
            f"{snapshot.backend}"
        ),
        (
            "Support:       "
            "BASIC"
        ),
        (
            "Size:          "
            f"{format_file_size(snapshot.size_bytes)}"
        ),
        (
            "Resolution:    "
            f"{snapshot.resolution}"
        ),
        (
            "Pixel mode:    "
            f"{snapshot.mode}"
        ),
        (
            "Frames:        "
            f"{snapshot.frame_count}"
        ),
        (
            "Animated:      "
            + (
                "YES"
                if snapshot.animated
                else "NO"
            )
        ),
        (
            "SHA256:        "
            f"{snapshot.sha256}"
        ),
        "",
        "METADATA",
        "-" * 60,
        (
            "EXIF:          "
            f"{snapshot.exif_status}"
        ),
        (
            "EXIF GPS:      "
            f"{snapshot.exif_gps_status}"
        ),
        (
            "XMP:           "
            f"{snapshot.xmp_status}"
        ),
        (
            "ICC:           "
            f"{snapshot.icc_status}"
        ),
        "",
        "DEVICE / CAPTURE",
        "-" * 60,
        (
            "Camera Make:   "
            f"{snapshot.camera_make or '-'}"
        ),
        (
            "Camera Model:  "
            f"{snapshot.camera_model or '-'}"
        ),
        (
            "Software:      "
            f"{snapshot.software or '-'}"
        ),
        (
            "Artist:        "
            f"{snapshot.artist or '-'}"
        ),
        (
            "Date Original: "
            f"{snapshot.datetime_original or '-'}"
        ),
        (
            "Orientation:   "
            + (
                (
                    f"{snapshot.orientation_raw} "
                    f"({snapshot.orientation_interpreted})"
                )
                if snapshot.orientation_raw
                is not None
                else "-"
            )
        ),
        "",
        "SUPPORT NOTE",
        "-" * 60,
        (
            f"{snapshot.format} currently uses "
            "PhotoMeta's BASIC external-backend "
            "scan."
        ),
        (
            "JPEG remains the FULL native "
            "forensic metadata pipeline."
        ),
        (
            "Privacy scoring, GPS normalization, "
            "scrubbing, anomaly analysis and "
            "comparison are not yet claimed "
            f"for {snapshot.format}."
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
                f"- {warning}"
            )

    return "\n".join(
        lines
    )
