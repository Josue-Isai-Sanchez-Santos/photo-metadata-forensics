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


@dataclass(frozen=True)
class IfdEntry:
    tag: int
    field_type: int
    count: int
    value_or_offset: bytes

    @property
    def tag_hex(self) -> str:
        return f"0x{self.tag:04X}"


@dataclass(frozen=True)
class Ifd:
    offset: int
    entries: tuple[IfdEntry, ...]
    next_ifd_offset: int


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


def parse_ifd(
    data: bytes,
    offset: int,
    byte_order: str,
) -> Ifd:
    """
    Interpreta un Image File Directory (IFD).

    Estructura:

        2 bytes   número de entradas
        N * 12    entradas
        4 bytes   offset del siguiente IFD
    """

    if byte_order not in {"little", "big"}:
        raise TiffParserError(
            f"Byte order inválido: {byte_order!r}."
        )

    if offset < 0:
        raise TiffParserError(
            "El offset del IFD no puede ser negativo."
        )

    if offset + 2 > len(data):
        raise TiffParserError(
            f"El offset IFD {offset} está fuera "
            "de los límites del TIFF."
        )

    entry_count = int.from_bytes(
        data[offset:offset + 2],
        byteorder=byte_order,
    )

    entries_start = offset + 2
    entries_size = entry_count * 12
    next_ifd_position = entries_start + entries_size
    required_size = next_ifd_position + 4

    if required_size > len(data):
        raise TiffParserError(
            "El IFD está truncado: "
            f"declara {entry_count} entradas, "
            "pero no hay suficientes bytes."
        )

    entries: list[IfdEntry] = []

    for index in range(entry_count):

        entry_offset = entries_start + (index * 12)

        tag = int.from_bytes(
            data[entry_offset:entry_offset + 2],
            byteorder=byte_order,
        )

        field_type = int.from_bytes(
            data[entry_offset + 2:entry_offset + 4],
            byteorder=byte_order,
        )

        count = int.from_bytes(
            data[entry_offset + 4:entry_offset + 8],
            byteorder=byte_order,
        )

        value_or_offset = data[
            entry_offset + 8:entry_offset + 12
        ]

        entries.append(
            IfdEntry(
                tag=tag,
                field_type=field_type,
                count=count,
                value_or_offset=value_or_offset,
            )
        )

    next_ifd_offset = int.from_bytes(
        data[
            next_ifd_position:
            next_ifd_position + 4
        ],
        byteorder=byte_order,
    )

    return Ifd(
        offset=offset,
        entries=tuple(entries),
        next_ifd_offset=next_ifd_offset,
    )
