from __future__ import annotations

from photometa.fileinfo import (
    format_file_size,
)
from photometa.formats.raw_backend import (
    RawImageSnapshot,
)


def format_raw_scan_report(
    snapshot: RawImageSnapshot,
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
            "RAW variant:   "
            f"{snapshot.variant}"
        ),
        (
            "Backend:       "
            f"{snapshot.backend}"
        ),
        (
            "Support:       "
            f"{snapshot.support_level}"
        ),
        (
            "rawpy:         "
            f"{snapshot.rawpy_version}"
        ),
        (
            "LibRaw:        "
            f"{snapshot.libraw_version}"
        ),
        (
            "Size:          "
            f"{format_file_size(snapshot.size_bytes)}"
        ),
        (
            "SHA256:        "
            f"{snapshot.sha256}"
        ),
        "",
        "RAW GEOMETRY",
        "-" * 60,
        (
            "RAW size:      "
            f"{snapshot.raw_resolution}"
        ),
        (
            "Visible size:  "
            f"{snapshot.visible_resolution}"
        ),
        (
            "Top margin:    "
            f"{snapshot.top_margin}"
        ),
        (
            "Left margin:   "
            f"{snapshot.left_margin}"
        ),
        (
            "Crop width:    "
            f"{snapshot.crop_width}"
        ),
        (
            "Crop height:   "
            f"{snapshot.crop_height}"
        ),
        (
            "Pixel aspect:  "
            f"{snapshot.pixel_aspect}"
        ),
        (
            "Flip code:     "
            f"{snapshot.orientation_code}"
        ),
        "",
        "SENSOR",
        "-" * 60,
        (
            "RAW type:      "
            f"{snapshot.raw_type}"
        ),
        (
            "Colors:        "
            f"{snapshot.num_colors}"
        ),
        (
            "Color desc:    "
            f"{snapshot.color_description or '-'}"
        ),
        (
            "White level:   "
            + _format_value(
                snapshot.white_level
            )
        ),
        (
            "Black levels:  "
            + _format_sequence(
                snapshot
                .black_level_per_channel
            )
        ),
        (
            "Camera white:  "
            + _format_sequence(
                snapshot
                .camera_white_level_per_channel
            )
        ),
        (
            "Camera WB:     "
            + _format_sequence(
                snapshot
                .camera_white_balance
            )
        ),
        (
            "Daylight WB:   "
            + _format_sequence(
                snapshot
                .daylight_white_balance
            )
        ),
        "",
        "CAPTURE METADATA",
        "-" * 60,
        (
            "ISO:           "
            + _format_number(
                snapshot.iso_speed
            )
        ),
        (
            "Shutter:       "
            + _format_shutter(
                snapshot.shutter_speed
            )
        ),
        (
            "Aperture:      "
            + _format_aperture(
                snapshot.aperture
            )
        ),
        (
            "Focal length:  "
            + _format_focal(
                snapshot.focal_length
            )
        ),
        (
            "Timestamp:     "
            + (
                snapshot.timestamp.isoformat()
                if snapshot.timestamp
                is not None
                else "-"
            )
        ),
        (
            "Shot order:    "
            + _format_value(
                snapshot.shot_order
            )
        ),
        (
            "Artist:        "
            f"{snapshot.artist or '-'}"
        ),
        "",
        "LENS",
        "-" * 60,
        (
            "Make:          "
            f"{snapshot.lens_make or '-'}"
        ),
        (
            "Model:         "
            f"{snapshot.lens_model or '-'}"
        ),
        (
            "Min focal:     "
            + _format_focal(
                snapshot.lens_min_focal
            )
        ),
        (
            "Max focal:     "
            + _format_focal(
                snapshot.lens_max_focal
            )
        ),
        "",
        "SUPPORT NOTE",
        "-" * 60,
        (
            "RAW currently uses PhotoMeta's "
            "optional BASIC rawpy/LibRaw backend."
        ),
        (
            "The file is unpacked for metadata "
            "and sensor inspection, but PhotoMeta "
            "does not demosaic or postprocess it."
        ),
        (
            "JPEG remains the FULL native "
            "forensic metadata pipeline."
        ),
        (
            "Privacy scoring, normalized GPS, "
            "scrubbing, anomaly analysis, "
            "comparison, single-file JSON and "
            "HTML reporting are not yet claimed "
            "for RAW."
        ),
        (
            "RAW variant names are filename hints. "
            "LibRaw validation determines whether "
            "a candidate file is actually readable "
            "as RAW."
        ),
    ]

    if snapshot.enabled_features:

        lines.extend(
            (
                "",
                "LIBRAW FEATURES",
                "-" * 60,
                ", ".join(
                    snapshot.enabled_features
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


def _format_sequence(
    value: tuple[
        object,
        ...
    ]
    | None,
) -> str:

    if value is None:

        return "-"

    return (
        "["
        + ", ".join(
            str(item)
            for item
            in value
        )
        + "]"
    )


def _format_value(
    value: object | None,
) -> str:

    if value is None:

        return "-"

    return str(
        value
    )


def _format_number(
    value: float | None,
) -> str:

    if value is None:

        return "-"

    if value.is_integer():

        return str(
            int(value)
        )

    return (
        f"{value:.4f}"
        .rstrip("0")
        .rstrip(".")
    )


def _format_shutter(
    seconds: float | None,
) -> str:

    if seconds is None:

        return "-"

    if (
        seconds > 0
        and seconds < 1
    ):

        denominator = round(
            1 / seconds
        )

        if denominator > 0:

            return (
                f"{seconds:.8f} s "
                f"(~1/{denominator} s)"
            )

    return (
        f"{seconds:.8f} s"
    )


def _format_aperture(
    value: float | None,
) -> str:

    if value is None:

        return "-"

    return (
        f"f/{value:.2f}"
    )


def _format_focal(
    value: float | None,
) -> str:

    if value is None:

        return "-"

    return (
        f"{value:.2f} mm"
    )
