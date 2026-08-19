from __future__ import annotations

from dataclasses import dataclass


class TiffParserError(Exception):
    """Base exception for TIFF/EXIF parsing errors."""


@dataclass(frozen=True)
class TiffHeader:
    byte_order_marker: bytes
    byte_order: str
    magic_number: int
    first_ifd_offset: int

    @property
    def byte_order_name(self) -> str:
        if self.byte_order == "little":
            return "Little-endian (Intel / II)"

        return "Big-endian (Motorola / MM)"


def parse_tiff_header(data: bytes) -> TiffHeader:
    """
    Interpreta los primeros 8 bytes de una estructura TIFF.

    TIFF header:

        Bytes 0-1: byte order
        Bytes 2-3: magic number (42)
        Bytes 4-7: offset del primer IFD
    """

    if len(data) < 8:
        raise TiffParserError(
            "La cabecera TIFF necesita al menos 8 bytes."
        )

    byte_order_marker = data[0:2]

    if byte_order_marker == b"II":
        byte_order = "little"

    elif byte_order_marker == b"MM":
        byte_order = "big"

    else:
        raise TiffParserError(
            "Byte order TIFF inválido: "
            f"{byte_order_marker!r}. "
            "Se esperaba b'II' o b'MM'."
        )

    magic_number = int.from_bytes(
        data[2:4],
        byteorder=byte_order,
    )

    if magic_number != 42:
        raise TiffParserError(
            "Magic number TIFF inválido: "
            f"{magic_number}. Se esperaba 42."
        )

    first_ifd_offset = int.from_bytes(
        data[4:8],
        byteorder=byte_order,
    )

    return TiffHeader(
        byte_order_marker=byte_order_marker,
        byte_order=byte_order,
        magic_number=magic_number,
        first_ifd_offset=first_ifd_offset,
    )
