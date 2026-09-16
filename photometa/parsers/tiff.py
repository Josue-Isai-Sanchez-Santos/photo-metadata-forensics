from __future__ import annotations

import struct
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from photometa.parsers.limits import (
    DEFAULT_PARSER_LIMITS,
    ParserLimits,
)


class TiffParserError(Exception):
    """Base exception for TIFF/EXIF parsing errors."""


TIFF_TYPE_SIZES: dict[int, int] = {
    1: 1,   # BYTE
    2: 1,   # ASCII
    3: 2,   # SHORT
    4: 4,   # LONG
    5: 8,   # RATIONAL
    6: 1,   # SBYTE
    7: 1,   # UNDEFINED
    8: 2,   # SSHORT
    9: 4,   # SLONG
    10: 8,  # SRATIONAL
    11: 4,  # FLOAT
    12: 8,  # DOUBLE
}


TIFF_TYPE_NAMES: dict[int, str] = {
    1: "BYTE",
    2: "ASCII",
    3: "SHORT",
    4: "LONG",
    5: "RATIONAL",
    6: "SBYTE",
    7: "UNDEFINED",
    8: "SSHORT",
    9: "SLONG",
    10: "SRATIONAL",
    11: "FLOAT",
    12: "DOUBLE",
}


DecodedTiffScalar: TypeAlias = (
    int
    | float
    | str
    | bytes
    | Fraction
)


DecodedTiffValue: TypeAlias = (
    DecodedTiffScalar
    | tuple[int, ...]
    | tuple[float, ...]
    | tuple[Fraction, ...]
)


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

    @property
    def field_type_name(self) -> str:
        return TIFF_TYPE_NAMES.get(
            self.field_type,
            f"UNKNOWN_{self.field_type}",
        )


@dataclass
class IfdTraversalState:
    visited_offsets: set[int]
    nodes_visited: int = 0

    @classmethod
    def create(
        cls,
        *,
        root_offset: int | None = None,
    ) -> "IfdTraversalState":

        visited_offsets: set[int] = set()
        nodes_visited = 0

        if root_offset is not None:

            visited_offsets.add(
                root_offset
            )

            nodes_visited = 1

        return cls(
            visited_offsets=visited_offsets,
            nodes_visited=nodes_visited,
        )


@dataclass(frozen=True)
class Ifd:
    offset: int
    entries: tuple[IfdEntry, ...]
    next_ifd_offset: int


def parse_tiff_header(data: bytes) -> TiffHeader:
    """
    Interpreta los primeros 8 bytes de una estructura TIFF.

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
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> Ifd:
    """
    Interpreta un Image File Directory (IFD).

    Estructura:

        2 bytes   número de entradas
        N * 12    entradas IFD
        4 bytes   offset del siguiente IFD
    """

    _validate_byte_order(byte_order)

    if offset < 8:
        raise TiffParserError(
            "El offset de un IFD debe estar "
            "después de la cabecera TIFF: "
            f"{offset}."
        )

    _validate_span(
        start=offset,
        length=2,
        total_size=len(data),
        context="cabecera del IFD",
    )

    entry_count = int.from_bytes(
        data[offset:offset + 2],
        byteorder=byte_order,
    )

    if (
        entry_count
        > limits.max_ifd_entries
    ):
        raise TiffParserError(
            "El IFD declara demasiadas entradas: "
            f"{entry_count} > "
            f"{limits.max_ifd_entries}."
        )

    entries_start = offset + 2

    entries_size = (
        entry_count * 12
    )

    _validate_span(
        start=entries_start,
        length=entries_size,
        total_size=len(data),
        context="tabla de entradas IFD",
    )

    next_ifd_position = (
        entries_start
        + entries_size
    )

    _validate_span(
        start=next_ifd_position,
        length=4,
        total_size=len(data),
        context="puntero al siguiente IFD",
    )

    entries: list[IfdEntry] = []

    for index in range(entry_count):

        entry_offset = (
            entries_start
            + (index * 12)
        )

        tag = int.from_bytes(
            data[
                entry_offset:
                entry_offset + 2
            ],
            byteorder=byte_order,
        )

        field_type = int.from_bytes(
            data[
                entry_offset + 2:
                entry_offset + 4
            ],
            byteorder=byte_order,
        )

        count = int.from_bytes(
            data[
                entry_offset + 4:
                entry_offset + 8
            ],
            byteorder=byte_order,
        )

        value_or_offset = data[
            entry_offset + 8:
            entry_offset + 12
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

    if next_ifd_offset != 0:

        if next_ifd_offset == offset:
            raise TiffParserError(
                "El IFD contiene un puntero "
                "next_ifd auto-referencial."
            )

        if next_ifd_offset < 8:
            raise TiffParserError(
                "El puntero next_ifd apunta "
                "dentro de la cabecera TIFF."
            )

        _validate_span(
            start=next_ifd_offset,
            length=2,
            total_size=len(data),
            context="siguiente IFD",
        )

    return Ifd(
        offset=offset,
        entries=tuple(entries),
        next_ifd_offset=next_ifd_offset,
    )


def parse_ifd_guarded(
    data: bytes,
    offset: int,
    byte_order: str,
    *,
    state: IfdTraversalState,
    depth: int,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> Ifd:
    """
    Parse one IFD while enforcing traversal
    budgets and detecting repeated offsets.

    Re-visiting an offset is treated as a
    circular pointer rather than silently
    parsing the same IFD again.
    """

    if depth < 0:

        raise TiffParserError(
            "La profundidad IFD no puede "
            "ser negativa."
        )

    if (
        depth
        > limits.max_ifd_depth
    ):

        raise TiffParserError(
            "Se excedió la profundidad "
            "máxima de recorrido IFD: "
            f"{depth} > "
            f"{limits.max_ifd_depth}."
        )

    if offset in state.visited_offsets:

        raise TiffParserError(
            "Se detectó un puntero IFD "
            "circular o repetido: "
            f"offset={offset}."
        )

    if (
        state.nodes_visited
        >= limits.max_ifd_nodes
    ):

        raise TiffParserError(
            "Se excedió el número máximo "
            "de IFDs permitidos durante "
            "el recorrido."
        )

    state.visited_offsets.add(
        offset
    )

    state.nodes_visited += 1

    return parse_ifd(
        data,
        offset,
        byte_order,
        limits=limits,
    )


def get_ifd_entry_data_size(
    entry: IfdEntry,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> int:
    """
    Calcula cuántos bytes ocupa el valor
    completo de una entrada IFD.
    """

    type_size = TIFF_TYPE_SIZES.get(
        entry.field_type
    )

    if type_size is None:
        raise TiffParserError(
            "Tipo TIFF no soportado: "
            f"{entry.field_type}."
        )

    if (
        entry.count
        > limits.max_tiff_components
    ):
        raise TiffParserError(
            "El valor TIFF declara demasiados "
            "componentes: "
            f"{entry.count} > "
            f"{limits.max_tiff_components}."
        )

    if (
        entry.count
        > (
            limits.max_tiff_value_bytes
            // type_size
        )
    ):
        raise TiffParserError(
            "El valor TIFF excede el límite "
            "de bytes permitido."
        )

    data_size = (
        type_size
        * entry.count
    )

    if (
        data_size
        > limits.max_tiff_value_bytes
    ):
        raise TiffParserError(
            "El valor TIFF excede el límite "
            "de bytes permitido: "
            f"{data_size} bytes."
        )

    return data_size


def get_ifd_entry_raw_value(
    data: bytes,
    entry: IfdEntry,
    byte_order: str,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> bytes:
    """
    Obtiene los bytes reales asociados a una
    entrada IFD.

    Si ocupan 4 bytes o menos:
        Value/Offset contiene el valor.

    Si ocupan más de 4 bytes:
        Value/Offset contiene un offset relativo
        al comienzo de la estructura TIFF.
    """

    _validate_byte_order(byte_order)

    if len(entry.value_or_offset) != 4:
        raise TiffParserError(
            "El campo Value/Offset de una entrada IFD "
            "debe contener exactamente 4 bytes."
        )

    data_size = get_ifd_entry_data_size(
        entry,
        limits=limits,
    )

    if data_size <= 4:
        return entry.value_or_offset[
            :data_size
        ]

    value_offset = int.from_bytes(
        entry.value_or_offset,
        byteorder=byte_order,
    )

    _validate_span(
        start=value_offset,
        length=data_size,
        total_size=len(data),
        context=(
            "valor TIFF externo "
            f"del tag {entry.tag_hex}"
        ),
    )

    value_end = (
        value_offset
        + data_size
    )

    return data[
        value_offset:value_end
    ]


def decode_ascii_value(
    raw_value: bytes,
) -> str:
    """
    Convierte bytes TIFF ASCII a str.
    """

    cleaned = raw_value.rstrip(
        b"\x00"
    )

    try:
        return cleaned.decode(
            "ascii"
        )

    except UnicodeDecodeError as exc:
        raise TiffParserError(
            "El valor declarado como ASCII "
            "contiene bytes no ASCII."
        ) from exc


def decode_ifd_value(
    data: bytes,
    entry: IfdEntry,
    byte_order: str,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> DecodedTiffValue:
    """
    Interpreta automáticamente una entrada IFD.

    Count = 1:
        devuelve un valor escalar.

    Count > 1:
        devuelve una tupla, excepto:

        ASCII -> str
        UNDEFINED -> bytes
    """

    _validate_byte_order(
        byte_order
    )

    raw = get_ifd_entry_raw_value(
        data,
        entry,
        byte_order,
        limits=limits,
    )

    field_type = entry.field_type

    if field_type == 1:
        # BYTE
        return _collapse(
            tuple(raw)
        )

    if field_type == 2:
        # ASCII
        return decode_ascii_value(
            raw
        )

    if field_type == 3:
        # SHORT
        return _decode_integer_components(
            raw,
            component_size=2,
            byte_order=byte_order,
            signed=False,
        )

    if field_type == 4:
        # LONG
        return _decode_integer_components(
            raw,
            component_size=4,
            byte_order=byte_order,
            signed=False,
        )

    if field_type == 5:
        # RATIONAL
        return _decode_rational_components(
            raw,
            byte_order=byte_order,
            signed=False,
        )

    if field_type == 6:
        # SBYTE
        values = tuple(
            int.from_bytes(
                raw[index:index + 1],
                byteorder=byte_order,
                signed=True,
            )
            for index in range(
                len(raw)
            )
        )

        return _collapse(
            values
        )

    if field_type == 7:
        # UNDEFINED
        return raw

    if field_type == 8:
        # SSHORT
        return _decode_integer_components(
            raw,
            component_size=2,
            byte_order=byte_order,
            signed=True,
        )

    if field_type == 9:
        # SLONG
        return _decode_integer_components(
            raw,
            component_size=4,
            byte_order=byte_order,
            signed=True,
        )

    if field_type == 10:
        # SRATIONAL
        return _decode_rational_components(
            raw,
            byte_order=byte_order,
            signed=True,
        )

    if field_type == 11:
        # FLOAT
        return _decode_float_components(
            raw,
            component_size=4,
            byte_order=byte_order,
        )

    if field_type == 12:
        # DOUBLE
        return _decode_float_components(
            raw,
            component_size=8,
            byte_order=byte_order,
        )

    raise TiffParserError(
        "Tipo TIFF no soportado: "
        f"{field_type}."
    )


def _validate_span(
    *,
    start: int,
    length: int,
    total_size: int,
    context: str,
) -> None:
    """
    Validate [start, start + length) without
    trusting attacker-controlled arithmetic.

    Python integers do not wrap, but checking
    length against total_size - start avoids
    constructing or accepting absurd spans.
    """

    if start < 0:
        raise TiffParserError(
            f"Offset negativo para {context}: "
            f"{start}."
        )

    if length < 0:
        raise TiffParserError(
            f"Longitud negativa para {context}: "
            f"{length}."
        )

    if start > total_size:
        raise TiffParserError(
            f"Offset fuera de límites para "
            f"{context}: {start} > "
            f"{total_size}."
        )

    if length > (
        total_size - start
    ):
        raise TiffParserError(
            f"Rango truncado o fuera de límites "
            f"para {context}: "
            f"offset={start}, "
            f"tamaño={length}, "
            f"longitud={total_size}."
        )


def _validate_byte_order(
    byte_order: str,
) -> None:

    if byte_order not in {
        "little",
        "big",
    }:
        raise TiffParserError(
            f"Byte order inválido: "
            f"{byte_order!r}."
        )


def _collapse(
    values: tuple[int, ...]
    | tuple[float, ...]
    | tuple[Fraction, ...],
) -> (
    int
    | float
    | Fraction
    | tuple[int, ...]
    | tuple[float, ...]
    | tuple[Fraction, ...]
):

    if len(values) == 1:
        return values[0]

    return values


def _decode_integer_components(
    raw: bytes,
    component_size: int,
    byte_order: str,
    signed: bool,
) -> (
    int
    | tuple[int, ...]
):

    if len(raw) % component_size != 0:
        raise TiffParserError(
            "El tamaño del valor TIFF "
            "no coincide con el tipo declarado."
        )

    values = tuple(
        int.from_bytes(
            raw[
                index:
                index + component_size
            ],
            byteorder=byte_order,
            signed=signed,
        )
        for index in range(
            0,
            len(raw),
            component_size,
        )
    )

    return _collapse(
        values
    )


def _decode_rational_components(
    raw: bytes,
    byte_order: str,
    signed: bool,
) -> (
    Fraction
    | tuple[Fraction, ...]
):

    if len(raw) % 8 != 0:
        raise TiffParserError(
            "Un valor RATIONAL/SRATIONAL "
            "debe ocupar múltiplos de 8 bytes."
        )

    values: list[Fraction] = []

    for index in range(
        0,
        len(raw),
        8,
    ):

        numerator = int.from_bytes(
            raw[
                index:
                index + 4
            ],
            byteorder=byte_order,
            signed=signed,
        )

        denominator = int.from_bytes(
            raw[
                index + 4:
                index + 8
            ],
            byteorder=byte_order,
            signed=signed,
        )

        if denominator == 0:
            raise TiffParserError(
                "RATIONAL/SRATIONAL inválido: "
                "el denominador no puede ser 0."
            )

        values.append(
            Fraction(
                numerator,
                denominator,
            )
        )

    return _collapse(
        tuple(values)
    )


def _decode_float_components(
    raw: bytes,
    component_size: int,
    byte_order: str,
) -> (
    float
    | tuple[float, ...]
):

    if len(raw) % component_size != 0:
        raise TiffParserError(
            "El tamaño del valor FLOAT/DOUBLE "
            "no coincide con el tipo declarado."
        )

    prefix = (
        "<"
        if byte_order == "little"
        else ">"
    )

    if component_size == 4:
        format_code = "f"

    elif component_size == 8:
        format_code = "d"

    else:
        raise TiffParserError(
            "Tamaño FLOAT/DOUBLE "
            "no soportado."
        )

    values = tuple(
        struct.unpack(
            prefix + format_code,
            raw[
                index:
                index + component_size
            ],
        )[0]
        for index in range(
            0,
            len(raw),
            component_size,
        )
    )

    return _collapse(
        values
    )
