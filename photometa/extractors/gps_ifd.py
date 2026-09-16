from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from photometa.parsers.exif import (
    ExifData,
    parse_exif,
)
from photometa.parsers.jpeg import (
    iter_jpeg_segments,
)
from photometa.parsers.limits import (
    DEFAULT_PARSER_LIMITS,
    ParserLimits,
)
from photometa.parsers.tags import (
    get_gps_tag_name,
)
from photometa.parsers.tiff import (
    DecodedTiffValue,
    Ifd,
    IfdTraversalState,
    decode_ifd_value,
    parse_ifd_guarded,
)

GPS_IFD_POINTER_TAG = 0x8825


class GpsIfdExtractorError(Exception):
    """Base exception for GPS IFD extraction errors."""


@dataclass(frozen=True)
class GpsMetadataEntry:
    tag: int
    tag_name: str
    field_type: int
    field_type_name: str
    count: int
    value: DecodedTiffValue

    @property
    def tag_hex(self) -> str:
        return f"0x{self.tag:04X}"


@dataclass(frozen=True)
class GpsMetadata:
    offset: int
    entries: tuple[GpsMetadataEntry, ...]

    def get(
        self,
        name: str,
        default: object | None = None,
    ) -> object:

        for entry in self.entries:
            if entry.tag_name == name:
                return entry.value

        return default

    def as_dict(
        self,
    ) -> dict[str, DecodedTiffValue]:

        return {
            entry.tag_name: entry.value
            for entry in self.entries
        }


@dataclass(frozen=True)
class LocationSummary:
    gps_detected: bool
    latitude: float | None
    longitude: float | None
    altitude: float | None
    altitude_ref: int | None
    altitude_reference: str | None
    gps_date: str | None
    gps_time: str | None
    image_direction: float | None


def _get_gps_ifd_pointer(
    exif: ExifData,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> int:

    pointer_entry = next(
        (
            entry
            for entry in exif.ifd0.entries
            if entry.tag == GPS_IFD_POINTER_TAG
        ),
        None,
    )

    if pointer_entry is None:
        raise GpsIfdExtractorError(
            "IFD0 no contiene GPSInfoIFDPointer."
        )

    value = decode_ifd_value(
        exif.tiff_data,
        pointer_entry,
        exif.header.byte_order,
        limits=limits,
    )

    if not isinstance(value, int):
        raise GpsIfdExtractorError(
            "GPSInfoIFDPointer no contiene "
            "un offset entero válido."
        )

    if value <= 0:
        raise GpsIfdExtractorError(
            f"GPSInfoIFDPointer inválido: {value}."
        )

    return value


def parse_gps_ifd(
    exif: ExifData,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> Ifd:
    """
    Sigue GPSInfoIFDPointer desde IFD0.
    """

    offset = _get_gps_ifd_pointer(
        exif,
        limits=limits,
    )

    state = IfdTraversalState.create(
        root_offset=exif.ifd0.offset,
    )

    return parse_ifd_guarded(
        exif.tiff_data,
        offset,
        exif.header.byte_order,
        state=state,
        depth=1,
        limits=limits,
    )


def extract_gps_ifd_metadata(
    exif: ExifData,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> GpsMetadata:
    """
    Decodifica todas las entradas del GPS IFD.
    """

    gps_ifd = parse_gps_ifd(
        exif,
        limits=limits,
    )

    entries: list[
        GpsMetadataEntry
    ] = []

    for entry in gps_ifd.entries:

        value = decode_ifd_value(
            exif.tiff_data,
            entry,
            exif.header.byte_order,
            limits=limits,
        )

        entries.append(
            GpsMetadataEntry(
                tag=entry.tag,
                tag_name=get_gps_tag_name(
                    entry.tag
                ),
                field_type=entry.field_type,
                field_type_name=(
                    entry.field_type_name
                ),
                count=entry.count,
                value=value,
            )
        )

    return GpsMetadata(
        offset=gps_ifd.offset,
        entries=tuple(entries),
    )


def extract_gps_ifd_from_jpeg(
    path: str | Path,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> GpsMetadata:
    """
    Extrae GPS IFD directamente desde un JPEG.
    """

    exif_segment = next(
        (
            segment
            for segment in iter_jpeg_segments(
                path,
                limits=limits,
            )
            if segment.is_exif
        ),
        None,
    )

    if exif_segment is None:
        raise GpsIfdExtractorError(
            "No se encontró un segmento APP1 EXIF."
        )

    exif = parse_exif(
        exif_segment,
        limits=limits,
    )

    return extract_gps_ifd_metadata(
        exif,
        limits=limits,
    )


def dms_to_decimal(
    dms: object,
    reference: object,
) -> float:
    """
    Convierte coordenadas GPS EXIF:

        grados, minutos, segundos

    a grados decimales.

    S y W producen coordenadas negativas.
    """

    if not isinstance(dms, tuple):
        raise GpsIfdExtractorError(
            "La coordenada GPS debe contener "
            "grados, minutos y segundos."
        )

    if len(dms) != 3:
        raise GpsIfdExtractorError(
            "La coordenada GPS debe contener "
            "exactamente tres componentes."
        )

    if not isinstance(reference, str):
        raise GpsIfdExtractorError(
            "La referencia GPS debe ser "
            "N, S, E o W."
        )

    components: list[Fraction] = []

    for value in dms:

        if isinstance(value, Fraction):
            components.append(value)

        elif isinstance(value, int):
            components.append(
                Fraction(value, 1)
            )

        else:
            raise GpsIfdExtractorError(
                "Componente GPS inválido."
            )

    degrees, minutes, seconds = components

    if degrees < 0:
        raise GpsIfdExtractorError(
            "Los grados GPS no deben ser negativos; "
            "el hemisferio se indica mediante Ref."
        )

    if not (
        Fraction(0, 1)
        <= minutes
        < Fraction(60, 1)
    ):
        raise GpsIfdExtractorError(
            "Los minutos GPS deben estar "
            "entre 0 y 60."
        )

    if not (
        Fraction(0, 1)
        <= seconds
        < Fraction(60, 1)
    ):
        raise GpsIfdExtractorError(
            "Los segundos GPS deben estar "
            "entre 0 y 60."
        )

    decimal = (
        degrees
        + (minutes / 60)
        + (seconds / 3600)
    )

    ref = reference.strip().upper()

    if ref in {"S", "W"}:
        decimal = -decimal

    elif ref not in {"N", "E"}:
        raise GpsIfdExtractorError(
            f"Referencia GPS inválida: {reference!r}."
        )

    return float(decimal)


def build_location_summary(
    metadata: GpsMetadata,
) -> LocationSummary:
    """
    Genera una representación amigable
    de los datos GPS.
    """

    latitude = _coordinate_or_none(
        metadata.get("GPSLatitude"),
        metadata.get("GPSLatitudeRef"),
    )

    longitude = _coordinate_or_none(
        metadata.get("GPSLongitude"),
        metadata.get("GPSLongitudeRef"),
    )

    (
        altitude,
        altitude_ref,
        altitude_reference,
    ) = _altitude_details(
        metadata.get("GPSAltitude"),
        metadata.get("GPSAltitudeRef"),
    )

    gps_time = _format_gps_time(
        metadata.get("GPSTimeStamp")
    )

    gps_date = _format_gps_date(
        metadata.get("GPSDateStamp")
    )

    image_direction = _number_or_none(
        metadata.get(
            "GPSImgDirection"
        )
    )

    return LocationSummary(
        gps_detected=True,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        altitude_ref=altitude_ref,
        altitude_reference=altitude_reference,
        gps_date=gps_date,
        gps_time=gps_time,
        image_direction=image_direction,
    )


def _coordinate_or_none(
    coordinate: object,
    reference: object,
) -> float | None:

    if coordinate is None or reference is None:
        return None

    return dms_to_decimal(
        coordinate,
        reference,
    )


def _number_or_none(
    value: object,
) -> float | None:

    if isinstance(value, Fraction):
        return float(value)

    if isinstance(value, int):
        return float(value)

    return None


def _altitude_details(
    altitude: object,
    altitude_ref: object,
) -> tuple[
    float | None,
    int | None,
    str | None,
]:

    value = _number_or_none(
        altitude
    )

    ref = (
        altitude_ref
        if isinstance(altitude_ref, int)
        else None
    )

    if value is None:
        return (
            None,
            ref,
            None,
        )

    if ref == 0:
        return (
            abs(value),
            0,
            "positive ellipsoidal height",
        )

    if ref == 1:
        return (
            -abs(value),
            1,
            "negative ellipsoidal height",
        )

    if ref == 2:
        return (
            abs(value),
            2,
            "positive sea-level altitude",
        )

    if ref == 3:
        return (
            -abs(value),
            3,
            "negative sea-level altitude",
        )

    if ref is None:
        return (
            value,
            None,
            "reference not provided",
        )

    return (
        value,
        ref,
        f"unknown EXIF reference ({ref})",
    )


def _format_gps_time(
    value: object,
) -> str | None:

    if not isinstance(value, tuple):
        return None

    if len(value) != 3:
        return None

    converted: list[float] = []

    for component in value:

        number = _number_or_none(
            component
        )

        if number is None:
            return None

        converted.append(number)

    hours, minutes, seconds = converted

    if (
        not 0 <= hours < 24
        or not 0 <= minutes < 60
        or not 0 <= seconds < 60
    ):
        return None

    if seconds.is_integer():

        seconds_text = (
            f"{int(seconds):02d}"
        )

    else:

        seconds_text = (
            f"{seconds:06.3f}"
            .rstrip("0")
            .rstrip(".")
        )

        if seconds < 10:
            seconds_text = (
                "0" + seconds_text
            )

    return (
        f"{int(hours):02d}:"
        f"{int(minutes):02d}:"
        f"{seconds_text} UTC"
    )


def _format_gps_date(
    value: object,
) -> str | None:

    if not isinstance(value, str):
        return None

    parts = value.split(":")

    if len(parts) != 3:
        return value

    year, month, day = parts

    if not (
        len(year) == 4
        and len(month) == 2
        and len(day) == 2
    ):
        return value

    return (
        f"{year}-{month}-{day}"
    )
