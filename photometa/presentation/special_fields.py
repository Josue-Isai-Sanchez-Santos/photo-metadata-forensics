from __future__ import annotations

from dataclasses import dataclass

from photometa.extractors.exif_ifd import (
    ExifIfdMetadata,
)
from photometa.extractors.gps_ifd import (
    GpsMetadata,
)
from photometa.extractors.ifd0 import (
    Ifd0Metadata,
)
from photometa.interpretation.special_fields import (
    interpret_special_field,
)


@dataclass(frozen=True)
class SpecialField:
    name: str
    raw_value: object
    interpreted_value: str


def collect_special_fields(
    ifd0: Ifd0Metadata | None = None,
    exif_ifd: ExifIfdMetadata | None = None,
    gps: GpsMetadata | None = None,
) -> tuple[SpecialField, ...]:

    candidates: list[
        tuple[str, object]
    ] = []

    if ifd0 is not None:

        candidates.append(
            (
                "Orientation",
                ifd0.get("Orientation"),
            )
        )

    if exif_ifd is not None:

        for name in (
            "ExposureProgram",
            "MeteringMode",
            "Flash",
            "WhiteBalance",
            "SceneCaptureType",
            "ColorSpace",
        ):
            candidates.append(
                (
                    name,
                    exif_ifd.get(name),
                )
            )

    if gps is not None:

        candidates.append(
            (
                "GPSAltitudeRef",
                gps.get("GPSAltitudeRef"),
            )
        )

    result: list[
        SpecialField
    ] = []

    for name, value in candidates:

        if value is None:
            continue

        result.append(
            SpecialField(
                name=name,
                raw_value=value,
                interpreted_value=(
                    interpret_special_field(
                        name,
                        value,
                    )
                ),
            )
        )

    return tuple(result)


def format_special_fields_report(
    fields: tuple[
        SpecialField,
        ...
    ],
) -> str:

    lines = [
        "SPECIAL FIELDS",
        "-" * 45,
    ]

    for field in fields:

        lines.append(
            f"{field.name:<20}: "
            f"{field.interpreted_value}"
        )

    return "\n".join(
        lines
    )
