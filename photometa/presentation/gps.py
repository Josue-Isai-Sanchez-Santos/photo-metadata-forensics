from __future__ import annotations

from fractions import Fraction

from photometa.extractors.gps_ifd import (
    GpsMetadata,
    LocationSummary,
)


def format_location_report(
    summary: LocationSummary,
) -> str:
    """
    Genera una representación GPS amigable.

    Esta vista oculta los detalles TIFF/RATIONAL
    y muestra valores útiles para una persona.
    """

    lines = [
        "LOCATION",
        "-" * 45,
        (
            "GPS detected: "
            + (
                "YES"
                if summary.gps_detected
                else "NO"
            )
        ),
    ]

    if summary.latitude is not None:
        lines.append(
            f"Latitude:       "
            f"{summary.latitude:.6f}"
        )

    if summary.longitude is not None:
        lines.append(
            f"Longitude:      "
            f"{summary.longitude:.6f}"
        )

    if summary.altitude is not None:

        altitude_text = (
            f"{summary.altitude:g} m"
        )

        if summary.altitude_ref == 0:
            altitude_text += (
                " "
                "(EXIF reports above sea level)"
            )

        elif summary.altitude_ref == 1:
            altitude_text += (
                " "
                "(EXIF reports below sea level)"
            )

        elif (
            summary.altitude_reference
            == "reference not provided"
        ):
            altitude_text += (
                " "
                "(EXIF altitude reference "
                "not provided)"
            )

        elif (
            summary.altitude_reference
            is not None
        ):
            altitude_text += (
                " "
                f"(EXIF altitude reference: "
                f"{summary.altitude_reference})"
            )

        lines.append(
            f"Altitude:       "
            f"{altitude_text}"
        )

    if summary.gps_date is not None:
        lines.append(
            f"GPS Date:       "
            f"{summary.gps_date}"
        )

    if summary.gps_time is not None:
        lines.append(
            f"GPS Time:       "
            f"{summary.gps_time}"
        )

    if summary.image_direction is not None:
        lines.append(
            f"Image Direction:"
            f" {summary.image_direction:g}°"
        )

    return "\n".join(lines)


def format_gps_raw_report(
    metadata: GpsMetadata,
) -> str:
    """
    Genera una vista RAW/forense.

    Mantiene los valores racionales exactos
    sin mostrar la representación interna
    Fraction(...) de Python.
    """

    lines = [
        "GPS RAW / FORENSIC",
        "-" * 45,
        f"GPS IFD offset: {metadata.offset}",
    ]

    for entry in metadata.entries:

        value = _format_raw_value(
            entry.value
        )

        lines.append(
            f"{entry.tag_name:<28}: "
            f"{value}"
        )

    return "\n".join(lines)


def _format_raw_value(
    value: object,
) -> str:
    """
    Convierte valores internos TIFF a una
    representación forense legible.
    """

    if isinstance(value, Fraction):

        return (
            f"{value.numerator}/"
            f"{value.denominator}"
        )

    if isinstance(value, tuple):

        components = (
            _format_raw_value(item)
            for item in value
        )

        return (
            "("
            + ", ".join(components)
            + ")"
        )

    if isinstance(value, bytes):
        return value.hex(" ")

    if isinstance(value, str):
        return value

    return str(value)
