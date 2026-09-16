from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from photometa.parsers.jpeg import (
    JpegSegment,
    iter_jpeg_segments,
)
from photometa.parsers.limits import (
    DEFAULT_PARSER_LIMITS,
    ParserLimits,
)

ICC_IDENTIFIER = b"ICC_PROFILE\x00"

ICC_HEADER_SIZE = 128


PROFILE_CLASS_NAMES: dict[str, str] = {
    "scnr": "Input device",
    "mntr": "Display device",
    "prtr": "Output device",
    "link": "Device link",
    "spac": "Color space conversion",
    "abst": "Abstract",
    "nmcl": "Named color",
}


COLOR_SPACE_NAMES: dict[str, str] = {
    "XYZ ": "CIE XYZ",
    "Lab ": "CIELAB",
    "Luv ": "CIELUV",
    "YCbr": "YCbCr",
    "Yxy ": "CIE Yxy",
    "RGB ": "RGB",
    "GRAY": "Gray",
    "HSV ": "HSV",
    "HLS ": "HLS",
    "CMYK": "CMYK",
    "CMY ": "CMY",
    "2CLR": "2 color",
    "3CLR": "3 color",
    "4CLR": "4 color",
    "5CLR": "5 color",
    "6CLR": "6 color",
    "7CLR": "7 color",
    "8CLR": "8 color",
    "9CLR": "9 color",
    "ACLR": "10 color",
    "BCLR": "11 color",
    "CCLR": "12 color",
    "DCLR": "13 color",
    "ECLR": "14 color",
    "FCLR": "15 color",
}


class IccParserError(Exception):
    """Base exception for ICC parsing errors."""


@dataclass(frozen=True)
class IccChunk:
    sequence_number: int
    total_chunks: int
    data: bytes


@dataclass(frozen=True)
class IccTagEntry:
    signature: str
    offset: int
    size: int


@dataclass(frozen=True)
class IccHeader:
    profile_size: int

    version_major: int
    version_minor: int
    version_bugfix: int

    profile_class_signature: str
    profile_class: str

    color_space_signature: str
    color_space: str

    pcs_signature: str
    pcs: str

    cmm_type: str
    platform: str
    device_manufacturer: str
    device_model: str
    creator: str

    @property
    def version(self) -> str:
        return (
            f"{self.version_major}."
            f"{self.version_minor}."
            f"{self.version_bugfix}"
        )


@dataclass(frozen=True)
class IccProfile:
    raw_data: bytes
    header: IccHeader
    tags: tuple[IccTagEntry, ...]
    profile_name: str | None
    chunk_count: int

    @property
    def color_space(self) -> str:
        return self.header.color_space

    @property
    def profile_class(self) -> str:
        return self.header.profile_class

    @property
    def version(self) -> str:
        return self.header.version


def is_icc_segment(
    segment: JpegSegment,
) -> bool:
    """
    Detecta un fragmento ICC almacenado
    dentro de APP2 JPEG.
    """

    return (
        segment.marker == 0xE2
        and segment.payload.startswith(
            ICC_IDENTIFIER
        )
    )


def parse_icc_chunk(
    segment: JpegSegment,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> IccChunk:
    """
    Analiza la cabecera específica del
    fragmento ICC JPEG:

        ICC_PROFILE\\0
        sequence number
        total chunks
        profile data
    """

    if not is_icc_segment(
        segment
    ):
        raise IccParserError(
            "El segmento no contiene "
            "un perfil ICC."
        )

    header_size = (
        len(ICC_IDENTIFIER)
        + 2
    )

    if len(segment.payload) < header_size:
        raise IccParserError(
            "Fragmento ICC truncado."
        )

    position = len(
        ICC_IDENTIFIER
    )

    sequence_number = (
        segment.payload[position]
    )

    total_chunks = (
        segment.payload[
            position + 1
        ]
    )

    if sequence_number == 0:
        raise IccParserError(
            "El número de secuencia ICC "
            "no puede ser cero."
        )

    if total_chunks == 0:
        raise IccParserError(
            "El número total de fragmentos "
            "ICC no puede ser cero."
        )

    if (
        sequence_number
        > total_chunks
    ):
        raise IccParserError(
            "La secuencia ICC es mayor "
            "que el total de fragmentos."
        )

    if (
        total_chunks
        > limits.max_icc_chunks
    ):
        raise IccParserError(
            "El perfil ICC declara demasiados "
            "fragmentos: "
            f"{total_chunks} > "
            f"{limits.max_icc_chunks}."
        )

    chunk_data_size = (
        len(segment.payload)
        - header_size
    )

    if (
        chunk_data_size
        > limits.max_icc_profile_bytes
    ):
        raise IccParserError(
            "Un fragmento ICC excede el "
            "presupuesto máximo del perfil."
        )

    return IccChunk(
        sequence_number=sequence_number,
        total_chunks=total_chunks,
        data=segment.payload[
            header_size:
        ],
    )


def extract_icc_chunks_from_jpeg(
    path: str | Path,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> tuple[IccChunk, ...]:
    """
    Extrae todos los fragmentos APP2 ICC.
    """

    chunks: list[
        IccChunk
    ] = []

    for segment in iter_jpeg_segments(
        path,
        limits=limits,
    ):

        if is_icc_segment(
            segment
        ):

            if (
                len(chunks)
                >= limits.max_icc_chunks
            ):
                raise IccParserError(
                    "Se excedió el límite de "
                    "fragmentos ICC."
                )

            chunks.append(
                parse_icc_chunk(
                    segment,
                    limits=limits,
                )
            )

    return tuple(chunks)


def reassemble_icc_chunks(
    chunks: tuple[IccChunk, ...],
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> bytes:
    """
    Reconstruye un perfil ICC dividido
    entre múltiples segmentos APP2.
    """

    if not chunks:
        raise IccParserError(
            "No hay fragmentos ICC "
            "para reconstruir."
        )

    if (
        len(chunks)
        > limits.max_icc_chunks
    ):
        raise IccParserError(
            "Se excedió el límite de "
            "fragmentos ICC."
        )

    expected_total = (
        chunks[0].total_chunks
    )

    if (
        expected_total
        > limits.max_icc_chunks
    ):
        raise IccParserError(
            "El perfil ICC declara demasiados "
            "fragmentos."
        )

    for chunk in chunks:

        if (
            chunk.total_chunks
            != expected_total
        ):
            raise IccParserError(
                "Los fragmentos ICC "
                "declaran totales diferentes."
            )

    by_sequence: dict[
        int,
        IccChunk,
    ] = {}

    for chunk in chunks:

        if (
            chunk.sequence_number
            in by_sequence
        ):
            raise IccParserError(
                "Se encontró un número "
                "de secuencia ICC duplicado."
            )

        by_sequence[
            chunk.sequence_number
        ] = chunk

    if (
        len(by_sequence)
        != expected_total
    ):
        raise IccParserError(
            "Faltan fragmentos del "
            "perfil ICC."
        )

    expected_sequences = set(
        range(
            1,
            expected_total + 1,
        )
    )

    actual_sequences = set(
        by_sequence
    )

    if (
        actual_sequences
        != expected_sequences
    ):
        raise IccParserError(
            "La secuencia de fragmentos "
            "ICC está incompleta."
        )

    total_bytes = 0

    for sequence in range(
        1,
        expected_total + 1,
    ):

        chunk_size = len(
            by_sequence[
                sequence
            ].data
        )

        if (
            chunk_size
            > (
                limits.max_icc_profile_bytes
                - total_bytes
            )
        ):
            raise IccParserError(
                "El perfil ICC reconstruido "
                "excede el límite de seguridad."
            )

        total_bytes += (
            chunk_size
        )

    return b"".join(
        by_sequence[
            sequence
        ].data
        for sequence
        in range(
            1,
            expected_total + 1,
        )
    )


def parse_icc_profile(
    data: bytes,
    chunk_count: int = 1,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> IccProfile:
    """
    Analiza el encabezado ICC y su
    tabla básica de tags.
    """

    if (
        len(data)
        > limits.max_icc_profile_bytes
    ):
        raise IccParserError(
            "El perfil ICC excede el "
            "límite de seguridad."
        )

    if len(data) < ICC_HEADER_SIZE:
        raise IccParserError(
            "Perfil ICC demasiado pequeño."
        )

    profile_size = int.from_bytes(
        data[0:4],
        byteorder="big",
    )

    if profile_size < ICC_HEADER_SIZE:
        raise IccParserError(
            "El tamaño declarado del "
            "perfil ICC es inválido."
        )

    if (
        profile_size
        > limits.max_icc_profile_bytes
    ):
        raise IccParserError(
            "El tamaño declarado del perfil ICC "
            "excede el límite de seguridad."
        )

    if profile_size > len(data):
        raise IccParserError(
            "El perfil ICC está truncado."
        )

    #
    # Puede haber padding adicional en
    # el contenedor JPEG. Conservamos
    # únicamente el tamaño declarado
    # por el propio perfil.
    #
    profile_data = data[
        :profile_size
    ]

    if (
        profile_data[36:40]
        != b"acsp"
    ):
        raise IccParserError(
            "Firma ICC 'acsp' inválida "
            "o ausente."
        )

    header = _parse_icc_header(
        profile_data
    )

    tags = _parse_tag_table(
        profile_data,
        limits=limits,
    )

    profile_name = (
        _extract_profile_name(
            profile_data,
            tags,
        )
    )

    return IccProfile(
        raw_data=profile_data,
        header=header,
        tags=tags,
        profile_name=profile_name,
        chunk_count=chunk_count,
    )


def extract_icc_profile_from_jpeg(
    path: str | Path,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> IccProfile | None:
    """
    Extrae y reconstruye el perfil ICC
    de un JPEG.

    La ausencia de ICC no es un error.
    """

    chunks = (
        extract_icc_chunks_from_jpeg(
            path,
            limits=limits,
        )
    )

    if not chunks:
        return None

    data = reassemble_icc_chunks(
        chunks,
        limits=limits,
    )

    return parse_icc_profile(
        data,
        chunk_count=len(chunks),
        limits=limits,
    )


def _parse_icc_header(
    data: bytes,
) -> IccHeader:

    version_major = data[8]

    version_minor = (
        data[9] >> 4
    )

    version_bugfix = (
        data[9] & 0x0F
    )

    profile_class_signature = (
        _decode_signature(
            data[12:16]
        )
    )

    color_space_signature = (
        _decode_signature(
            data[16:20]
        )
    )

    pcs_signature = (
        _decode_signature(
            data[20:24]
        )
    )

    return IccHeader(
        profile_size=int.from_bytes(
            data[0:4],
            "big",
        ),
        version_major=version_major,
        version_minor=version_minor,
        version_bugfix=version_bugfix,
        profile_class_signature=(
            profile_class_signature
        ),
        profile_class=(
            PROFILE_CLASS_NAMES.get(
                profile_class_signature,
                (
                    "Unknown "
                    f"({profile_class_signature})"
                ),
            )
        ),
        color_space_signature=(
            color_space_signature
        ),
        color_space=(
            COLOR_SPACE_NAMES.get(
                color_space_signature,
                (
                    "Unknown "
                    f"({color_space_signature})"
                ),
            )
        ),
        pcs_signature=(
            pcs_signature
        ),
        pcs=(
            COLOR_SPACE_NAMES.get(
                pcs_signature,
                (
                    "Unknown "
                    f"({pcs_signature})"
                ),
            )
        ),
        cmm_type=_decode_signature(
            data[4:8]
        ),
        platform=_decode_signature(
            data[40:44]
        ),
        device_manufacturer=(
            _decode_signature(
                data[48:52]
            )
        ),
        device_model=(
            _decode_signature(
                data[52:56]
            )
        ),
        creator=_decode_signature(
            data[80:84]
        ),
    )


def _parse_tag_table(
    data: bytes,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> tuple[IccTagEntry, ...]:

    if len(data) < 132:
        return ()

    tag_count = int.from_bytes(
        data[128:132],
        byteorder="big",
    )

    if (
        tag_count
        > limits.max_icc_tags
    ):
        raise IccParserError(
            "El perfil ICC declara demasiados "
            "tags: "
            f"{tag_count} > "
            f"{limits.max_icc_tags}."
        )

    table_end = (
        132
        + (tag_count * 12)
    )

    if table_end > len(data):
        raise IccParserError(
            "Tabla de tags ICC truncada."
        )

    tags: list[
        IccTagEntry
    ] = []

    for index in range(
        tag_count
    ):

        position = (
            132
            + (index * 12)
        )

        signature = _decode_signature(
            data[
                position:
                position + 4
            ]
        )

        offset = int.from_bytes(
            data[
                position + 4:
                position + 8
            ],
            "big",
        )

        size = int.from_bytes(
            data[
                position + 8:
                position + 12
            ],
            "big",
        )

        if offset > len(data):
            raise IccParserError(
                f"Offset ICC inválido "
                f"para tag {signature!r}."
            )

        if (
            size
            > (
                len(data)
                - offset
            )
        ):
            raise IccParserError(
                f"Tag ICC truncado: "
                f"{signature!r}."
            )

        tags.append(
            IccTagEntry(
                signature=signature,
                offset=offset,
                size=size,
            )
        )

    return tuple(tags)


def _extract_profile_name(
    data: bytes,
    tags: tuple[
        IccTagEntry,
        ...
    ],
) -> str | None:
    """
    Busca profileDescriptionTag.

    Su firma de tag es 'desc', pero
    internamente puede utilizar descType
    o mlucType.
    """

    description_tag = next(
        (
            tag
            for tag in tags
            if tag.signature == "desc"
        ),
        None,
    )

    if description_tag is None:
        return None

    payload = data[
        description_tag.offset:
        description_tag.offset
        + description_tag.size
    ]

    if len(payload) < 8:
        return None

    type_signature = (
        _decode_signature(
            payload[0:4]
        )
    )

    if type_signature == "desc":
        return _parse_desc_type(
            payload
        )

    if type_signature == "mluc":
        return _parse_mluc_type(
            payload
        )

    return None


def _parse_desc_type(
    payload: bytes,
) -> str | None:

    if len(payload) < 12:
        return None

    ascii_count = int.from_bytes(
        payload[8:12],
        "big",
    )

    if ascii_count == 0:
        return None

    start = 12
    end = (
        start
        + ascii_count
    )

    if end > len(payload):
        raise IccParserError(
            "descType ICC truncado."
        )

    raw_name = payload[
        start:end
    ]

    raw_name = raw_name.rstrip(
        b"\x00"
    )

    if not raw_name:
        return None

    return raw_name.decode(
        "latin-1",
        errors="replace",
    )


def _parse_mluc_type(
    payload: bytes,
) -> str | None:
    """
    Analiza multiLocalizedUnicodeType.

    Preferimos:
        en-US
        en-*
        primer registro disponible
    """

    if len(payload) < 16:
        return None

    record_count = int.from_bytes(
        payload[8:12],
        "big",
    )

    record_size = int.from_bytes(
        payload[12:16],
        "big",
    )

    if record_size < 12:
        raise IccParserError(
            "Registro mluc ICC inválido."
        )

    table_end = (
        16
        + record_count
        * record_size
    )

    if table_end > len(payload):
        raise IccParserError(
            "Tabla mluc ICC truncada."
        )

    values: list[
        tuple[str, str, str]
    ] = []

    for index in range(
        record_count
    ):

        position = (
            16
            + index
            * record_size
        )

        language = payload[
            position:
            position + 2
        ].decode(
            "ascii",
            errors="replace",
        )

        country = payload[
            position + 2:
            position + 4
        ].decode(
            "ascii",
            errors="replace",
        )

        length = int.from_bytes(
            payload[
                position + 4:
                position + 8
            ],
            "big",
        )

        offset = int.from_bytes(
            payload[
                position + 8:
                position + 12
            ],
            "big",
        )

        end = (
            offset
            + length
        )

        if end > len(payload):
            raise IccParserError(
                "Texto mluc ICC truncado."
            )

        text = payload[
            offset:end
        ].decode(
            "utf-16-be",
            errors="replace",
        ).strip()

        if text:
            values.append(
                (
                    language,
                    country,
                    text,
                )
            )

    if not values:
        return None

    for language, country, text in values:

        if (
            language == "en"
            and country == "US"
        ):
            return text

    for language, _, text in values:

        if language == "en":
            return text

    return values[0][2]


def _decode_signature(
    value: bytes,
) -> str:

    return value.decode(
        "ascii",
        errors="replace",
    )
