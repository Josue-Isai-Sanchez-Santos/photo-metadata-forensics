from __future__ import annotations

from dataclasses import dataclass

from photometa.parsers.jpeg import JpegSegment
from photometa.parsers.tiff import (
    Ifd,
    TiffHeader,
    TiffParserError,
    parse_ifd,
    parse_tiff_header,
)


EXIF_IDENTIFIER = b"Exif\x00\x00"


class ExifParserError(Exception):
    """Base exception for EXIF parsing errors."""


@dataclass(frozen=True)
class ExifData:
    tiff_data: bytes
    header: TiffHeader
    ifd0: Ifd


def extract_tiff_data(
    segment: JpegSegment,
) -> bytes:
    """
    Extrae los bytes TIFF de un segmento APP1 EXIF.
    """

    if segment.marker != 0xE1:
        raise ExifParserError(
            "El segmento proporcionado no es APP1."
        )

    if not segment.payload.startswith(
        EXIF_IDENTIFIER
    ):
        raise ExifParserError(
            "El segmento APP1 no contiene "
            "el identificador Exif."
        )

    return segment.payload[
        len(EXIF_IDENTIFIER):
    ]


def parse_exif_tiff_header(
    segment: JpegSegment,
) -> TiffHeader:
    """
    Extrae e interpreta la cabecera TIFF
    de un segmento APP1 EXIF.
    """

    tiff_data = extract_tiff_data(segment)

    try:
        return parse_tiff_header(tiff_data)

    except TiffParserError as exc:
        raise ExifParserError(
            f"Cabecera TIFF inválida: {exc}"
        ) from exc


def parse_exif(
    segment: JpegSegment,
) -> ExifData:
    """
    Interpreta la estructura TIFF principal
    de un segmento APP1 EXIF.
    """

    tiff_data = extract_tiff_data(segment)

    try:
        header = parse_tiff_header(tiff_data)

        ifd0 = parse_ifd(
            tiff_data,
            header.first_ifd_offset,
            header.byte_order,
        )

    except TiffParserError as exc:
        raise ExifParserError(
            f"Estructura TIFF inválida: {exc}"
        ) from exc

    return ExifData(
        tiff_data=tiff_data,
        header=header,
        ifd0=ifd0,
    )
