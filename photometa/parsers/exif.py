from __future__ import annotations

from photometa.parsers.jpeg import JpegSegment
from photometa.parsers.tiff import (
    TiffHeader,
    TiffParserError,
    parse_tiff_header,
)


EXIF_IDENTIFIER = b"Exif\x00\x00"


class ExifParserError(Exception):
    """Base exception for EXIF parsing errors."""


def parse_exif_tiff_header(
    segment: JpegSegment,
) -> TiffHeader:
    """
    Extrae e interpreta la cabecera TIFF
    de un segmento APP1 EXIF.
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

    tiff_data = segment.payload[
        len(EXIF_IDENTIFIER):
    ]

    try:
        return parse_tiff_header(tiff_data)

    except TiffParserError as exc:
        raise ExifParserError(
            f"Cabecera TIFF inválida: {exc}"
        ) from exc
