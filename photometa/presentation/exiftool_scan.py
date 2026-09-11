from __future__ import annotations

from photometa.backends.exiftool_backend import (
    ExifToolSnapshot,
)
from photometa.fileinfo import (
    format_file_size,
)


def format_exiftool_scan_report(
    snapshot: ExifToolSnapshot,
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
            f"{snapshot.file_type or '-'}"
        ),
        (
            "MIME type:     "
            f"{snapshot.mime_type or '-'}"
        ),
        (
            "Backend:       "
            f"{snapshot.backend}"
        ),
        (
            "Backend mode:  "
            "OPTIONAL / EXTERNAL"
        ),
        (
            "ExifTool:      "
            f"{snapshot.exiftool_version}"
        ),
        (
            "Size:          "
            f"{format_file_size(snapshot.size_bytes)}"
        ),
        (
            "Resolution:    "
            f"{snapshot.resolution or '-'}"
        ),
        (
            "SHA256:        "
            f"{snapshot.sha256}"
        ),
        (
            "Tags returned: "
            f"{snapshot.tag_count}"
        ),
        "",
        "METADATA SUMMARY",
        "-" * 60,
        (
            "EXIF:          "
            f"{snapshot.exif_status}"
        ),
        (
            "GPS:           "
            f"{snapshot.gps_status}"
        ),
        (
            "XMP:           "
            f"{snapshot.xmp_status}"
        ),
        (
            "IPTC:          "
            f"{snapshot.iptc_status}"
        ),
        (
            "ICC:           "
            f"{snapshot.icc_status}"
        ),
        (
            "QuickTime:     "
            f"{snapshot.quicktime_status}"
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
            "Date Original: "
            f"{snapshot.datetime_original or '-'}"
        ),
        (
            "Lens Make:     "
            f"{snapshot.lens_make or '-'}"
        ),
        (
            "Lens Model:    "
            f"{snapshot.lens_model or '-'}"
        ),
        (
            "Orientation:   "
            f"{snapshot.orientation or '-'}"
        ),
        "",
        "EXIFTOOL GROUPS",
        "-" * 60,
    ]

    if snapshot.group_counts:

        for group, count in (
            snapshot.group_counts
        ):

            lines.append(
                f"{group:<20} {count}"
            )

    else:

        lines.append(
            "No grouped tags returned."
        )

    lines.extend(
        (
            "",
            "LOCATION PRIVACY",
            "-" * 60,
        )
    )

    if snapshot.gps_status == "YES":

        lines.extend(
            (
                "GPS metadata detected: YES",
                (
                    "Exact GPS values are hidden "
                    "by PhotoMeta's ExifTool "
                    "compatibility summary."
                ),
            )
        )

    else:

        lines.append(
            "GPS metadata detected: NO"
        )

    lines.extend(
        (
            "",
            "BACKEND NOTE",
            "-" * 60,
            (
                "This result was produced by "
                "the optional external ExifTool "
                "backend, not PhotoMeta's native "
                "metadata parser."
            ),
            (
                "Use the default backend to test "
                "PhotoMeta's own parser and "
                "format adapters."
            ),
            (
                "Differences between PhotoMeta "
                "and ExifTool are investigative "
                "information; they do not by "
                "themselves prove corruption, "
                "manipulation, authenticity or "
                "provenance."
            ),
            (
                "The compatibility summary does "
                "not print every metadata value "
                "returned internally by ExifTool."
            ),
        )
    )

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
