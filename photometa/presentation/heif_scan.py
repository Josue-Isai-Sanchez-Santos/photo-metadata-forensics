from __future__ import annotations

from photometa.fileinfo import (
    format_file_size,
)
from photometa.formats.heif_backend import (
    HeifImageSnapshot,
)


def format_heif_scan_report(
    snapshot: HeifImageSnapshot,
) -> str:

    brands = (
        ", ".join(
            snapshot.compatible_brands
        )
        if snapshot.compatible_brands
        else "-"
    )

    orientation = "-"

    if (
        snapshot.orientation_raw
        is not None
    ):

        orientation = (
            f"{snapshot.orientation_raw} "
            f"({snapshot.orientation_interpreted})"
        )

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
            "OPTIONAL / BASIC"
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
            "Images:        "
            f"{snapshot.image_count}"
        ),
        (
            "Bit depth:     "
            f"{snapshot.bit_depth or '-'}"
        ),
        (
            "Chroma:        "
            f"{snapshot.chroma or '-'}"
        ),
        (
            "Alpha:         "
            + (
                "YES"
                if snapshot.has_alpha
                else "NO"
            )
        ),
        (
            "SHA256:        "
            f"{snapshot.sha256}"
        ),
        "",
        "HEIF CONTAINER",
        "-" * 60,
        (
            "Major brand:   "
            f"{snapshot.major_brand}"
        ),
        (
            "Compatible:    "
            f"{brands}"
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
        (
            "NCLX:          "
            f"{snapshot.nclx_status}"
        ),
        (
            "Other blocks:  "
            f"{snapshot.other_metadata_blocks}"
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
            f"{orientation}"
        ),
        "",
        "SUPPORT NOTE",
        "-" * 60,
        (
            "HEIC/HEIF currently uses "
            "PhotoMeta's optional BASIC "
            "pillow-heif/libheif backend."
        ),
        (
            "JPEG remains the FULL native "
            "forensic metadata pipeline."
        ),
        (
            "Privacy scoring, normalized GPS, "
            "scrubbing, anomaly analysis, "
            "comparison, single-file JSON and "
            "HTML reporting are not yet "
            "claimed for HEIC/HEIF."
        ),
        (
            "HEIF EXIF orientation is reported "
            "as metadata only and is not used "
            "here to infer image rotation."
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
