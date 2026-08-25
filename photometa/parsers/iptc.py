from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from photometa.parsers.jpeg import (
    JpegSegment,
    iter_jpeg_segments,
)


PHOTOSHOP_IDENTIFIER = (
    b"Photoshop 3.0\x00"
)

PHOTOSHOP_RESOURCE_SIGNATURE = (
    b"8BIM"
)

IPTC_RESOURCE_ID = 0x0404

IPTC_DATASET_MARKER = 0x1C

IPTC_UTF8_DESIGNATOR = (
    b"\x1b%G"
)


IPTC_DATASET_NAMES: dict[
    tuple[int, int],
    str,
] = {
    (1, 90): "CodedCharacterSet",

    (2, 5): "ObjectName",
    (2, 25): "Keywords",
    (2, 40): "SpecialInstructions",
    (2, 55): "DateCreated",
    (2, 60): "TimeCreated",

    (2, 80): "Byline",
    (2, 85): "BylineTitle",

    (2, 90): "City",
    (2, 92): "Sublocation",
    (2, 95): "ProvinceState",

    (2, 100): "CountryCode",
    (2, 101): "CountryName",

    (
        2,
        103,
    ): "OriginalTransmissionReference",

    (2, 105): "Headline",
    (2, 110): "Credit",
    (2, 115): "Source",
    (2, 116): "CopyrightNotice",
    (2, 120): "CaptionAbstract",
    (2, 122): "WriterEditor",
}


TEXT_DATASETS = {
    dataset_id
    for dataset_id
    in IPTC_DATASET_NAMES
    if dataset_id != (1, 90)
}


IptcValue: TypeAlias = (
    str
    | bytes
)


class IptcParserError(Exception):
    """Base exception for IPTC parsing errors."""


@dataclass(frozen=True)
class PhotoshopResource:
    resource_id: int
    name: str
    data: bytes

    @property
    def resource_id_hex(
        self,
    ) -> str:

        return (
            f"0x{self.resource_id:04X}"
        )


@dataclass(frozen=True)
class IptcDataset:
    record_number: int
    dataset_number: int
    name: str
    raw_value: bytes
    value: IptcValue

    @property
    def identifier(
        self,
    ) -> str:

        return (
            f"{self.record_number}:"
            f"{self.dataset_number:02d}"
        )


@dataclass(frozen=True)
class IptcMetadata:
    raw_data: bytes
    datasets: tuple[
        IptcDataset,
        ...
    ]
    encoding: str

    def get(
        self,
        name: str,
        default: object | None = None,
    ) -> object:

        for dataset in self.datasets:

            if dataset.name == name:
                return dataset.value

        return default

    def get_all(
        self,
        name: str,
    ) -> tuple[IptcValue, ...]:

        return tuple(
            dataset.value
            for dataset
            in self.datasets
            if dataset.name == name
        )

    @property
    def title(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "ObjectName"
            )
        )

    @property
    def creators(
        self,
    ) -> tuple[str, ...]:

        return tuple(
            value
            for value
            in self.get_all(
                "Byline"
            )
            if isinstance(
                value,
                str,
            )
        )

    @property
    def creator(
        self,
    ) -> str | None:

        if self.creators:
            return self.creators[0]

        return None

    @property
    def headline(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "Headline"
            )
        )

    @property
    def caption(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "CaptionAbstract"
            )
        )

    @property
    def keywords(
        self,
    ) -> tuple[str, ...]:

        return tuple(
            value
            for value
            in self.get_all(
                "Keywords"
            )
            if isinstance(
                value,
                str,
            )
        )

    @property
    def copyright(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "CopyrightNotice"
            )
        )

    @property
    def sublocation(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "Sublocation"
            )
        )

    @property
    def city(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "City"
            )
        )

    @property
    def province_state(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "ProvinceState"
            )
        )

    @property
    def country_code(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "CountryCode"
            )
        )

    @property
    def country(
        self,
    ) -> str | None:

        return _as_text(
            self.get(
                "CountryName"
            )
        )


def is_photoshop_app13(
    segment: JpegSegment,
) -> bool:
    """
    Detecta un APP13 con estructura
    Photoshop Image Resources.
    """

    return (
        segment.marker == 0xED
        and segment.payload.startswith(
            PHOTOSHOP_IDENTIFIER
        )
    )


def parse_photoshop_resources(
    segment: JpegSegment,
) -> tuple[
    PhotoshopResource,
    ...
]:
    """
    Analiza los Image Resource Blocks
    contenidos en un APP13 Photoshop.
    """

    if not is_photoshop_app13(
        segment
    ):
        raise IptcParserError(
            "El segmento no es un "
            "APP13 Photoshop válido."
        )

    data = segment.payload

    position = len(
        PHOTOSHOP_IDENTIFIER
    )

    resources: list[
        PhotoshopResource
    ] = []

    while position < len(data):

        if (
            len(data) - position
            < 7
        ):
            raise IptcParserError(
                "Image Resource Block "
                "truncado."
            )

        signature = data[
            position:
            position + 4
        ]

        position += 4

        if (
            signature
            != PHOTOSHOP_RESOURCE_SIGNATURE
        ):
            raise IptcParserError(
                "Firma Photoshop Image "
                "Resource inválida."
            )

        resource_id = int.from_bytes(
            data[
                position:
                position + 2
            ],
            byteorder="big",
        )

        position += 2

        #
        # Pascal string:
        # 1 byte de longitud + nombre.
        #
        name_length = data[
            position
        ]

        position += 1

        name_end = (
            position
            + name_length
        )

        if name_end > len(data):
            raise IptcParserError(
                "Nombre Photoshop "
                "Resource truncado."
            )

        name_bytes = data[
            position:name_end
        ]

        position = name_end

        #
        # El Pascal string completo,
        # incluyendo su byte de longitud,
        # se rellena a longitud par.
        #
        if (
            (1 + name_length)
            % 2
            != 0
        ):
            position += 1

        if (
            position + 4
            > len(data)
        ):
            raise IptcParserError(
                "Tamaño Photoshop "
                "Resource truncado."
            )

        resource_size = int.from_bytes(
            data[
                position:
                position + 4
            ],
            byteorder="big",
        )

        position += 4

        resource_end = (
            position
            + resource_size
        )

        if resource_end > len(data):
            raise IptcParserError(
                "Datos Photoshop "
                "Resource truncados."
            )

        resource_data = data[
            position:
            resource_end
        ]

        position = resource_end

        #
        # Los datos de un IRB también
        # se rellenan a longitud par.
        #
        if resource_size % 2:
            position += 1

        if position > len(data):
            raise IptcParserError(
                "Padding Photoshop "
                "Resource truncado."
            )

        resources.append(
            PhotoshopResource(
                resource_id=resource_id,
                name=name_bytes.decode(
                    "latin-1",
                    errors="replace",
                ),
                data=resource_data,
            )
        )

    return tuple(
        resources
    )


def extract_iptc_resource(
    segment: JpegSegment,
) -> bytes | None:
    """
    Devuelve el recurso IPTC-NAA 0x0404
    de un APP13 Photoshop.
    """

    for resource in (
        parse_photoshop_resources(
            segment
        )
    ):

        if (
            resource.resource_id
            == IPTC_RESOURCE_ID
        ):
            return resource.data

    return None


def parse_iptc_iim(
    data: bytes,
) -> IptcMetadata:
    """
    Analiza una secuencia IPTC IIM.

    Cada DataSet comienza con:

        0x1C
        record number
        dataset number
        length
        value
    """

    raw_datasets = (
        _parse_raw_datasets(
            data
        )
    )

    encoding = (
        _detect_text_encoding(
            raw_datasets
        )
    )

    datasets: list[
        IptcDataset
    ] = []

    for (
        record_number,
        dataset_number,
        raw_value,
    ) in raw_datasets:

        dataset_id = (
            record_number,
            dataset_number,
        )

        name = (
            IPTC_DATASET_NAMES.get(
                dataset_id,
                (
                    "Unknown_"
                    f"{record_number}_"
                    f"{dataset_number}"
                ),
            )
        )

        value = _decode_dataset_value(
            dataset_id,
            raw_value,
            encoding,
        )

        datasets.append(
            IptcDataset(
                record_number=(
                    record_number
                ),
                dataset_number=(
                    dataset_number
                ),
                name=name,
                raw_value=raw_value,
                value=value,
            )
        )

    return IptcMetadata(
        raw_data=data,
        datasets=tuple(
            datasets
        ),
        encoding=encoding,
    )


def extract_iptc_from_jpeg(
    path: str | Path,
) -> IptcMetadata | None:
    """
    Extrae el primer recurso IPTC-NAA
    encontrado en APP13.

    La ausencia de IPTC no es un error.
    """

    for segment in iter_jpeg_segments(
        path
    ):

        if not is_photoshop_app13(
            segment
        ):
            continue

        resource = extract_iptc_resource(
            segment
        )

        if resource is not None:
            return parse_iptc_iim(
                resource
            )

    return None


def _parse_raw_datasets(
    data: bytes,
) -> list[
    tuple[
        int,
        int,
        bytes,
    ]
]:

    position = 0

    datasets: list[
        tuple[
            int,
            int,
            bytes,
        ]
    ] = []

    while position < len(data):

        if (
            len(data) - position
            < 5
        ):
            raise IptcParserError(
                "DataSet IPTC truncado."
            )

        if (
            data[position]
            != IPTC_DATASET_MARKER
        ):
            raise IptcParserError(
                "Marcador IPTC IIM "
                "inválido."
            )

        record_number = data[
            position + 1
        ]

        dataset_number = data[
            position + 2
        ]

        length_field = (
            int.from_bytes(
                data[
                    position + 3:
                    position + 5
                ],
                byteorder="big",
            )
        )

        position += 5

        #
        # Standard DataSet:
        #
        # bit más significativo = 0
        # los 15 bits restantes
        # contienen la longitud.
        #
        if (
            length_field
            & 0x8000
            == 0
        ):
            value_length = (
                length_field
            )

        else:
            #
            # Extended DataSet:
            #
            # los 15 bits inferiores
            # indican cuántos bytes
            # codifican la longitud real.
            #
            length_octets = (
                length_field
                & 0x7FFF
            )

            if length_octets == 0:
                raise IptcParserError(
                    "Longitud extendida "
                    "IPTC inválida."
                )

            if (
                position
                + length_octets
                > len(data)
            ):
                raise IptcParserError(
                    "Descriptor de longitud "
                    "IPTC truncado."
                )

            value_length = (
                int.from_bytes(
                    data[
                        position:
                        position
                        + length_octets
                    ],
                    byteorder="big",
                )
            )

            position += (
                length_octets
            )

        value_end = (
            position
            + value_length
        )

        if value_end > len(data):
            raise IptcParserError(
                "Valor IPTC truncado."
            )

        raw_value = data[
            position:value_end
        ]

        position = value_end

        datasets.append(
            (
                record_number,
                dataset_number,
                raw_value,
            )
        )

    return datasets


def _detect_text_encoding(
    datasets: list[
        tuple[
            int,
            int,
            bytes,
        ]
    ],
) -> str:
    """
    IIM 1:90 anuncia el juego
    de caracteres.

    ESC % G designa UTF-8.

    Si no está presente utilizamos
    latin-1 como fallback determinista,
    conservando siempre raw_value.
    """

    for (
        record_number,
        dataset_number,
        raw_value,
    ) in datasets:

        if (
            record_number == 1
            and dataset_number == 90
            and IPTC_UTF8_DESIGNATOR
            in raw_value
        ):
            return "utf-8"

    return "latin-1"


def _decode_dataset_value(
    dataset_id: tuple[int, int],
    raw_value: bytes,
    encoding: str,
) -> IptcValue:

    if dataset_id == (1, 90):

        if (
            IPTC_UTF8_DESIGNATOR
            in raw_value
        ):
            return "UTF-8"

        return raw_value

    if dataset_id in TEXT_DATASETS:

        return raw_value.decode(
            encoding,
            errors="replace",
        ).rstrip(
            "\x00"
        )

    #
    # No intentamos interpretar
    # DataSets desconocidos como texto.
    #
    return raw_value


def _as_text(
    value: object,
) -> str | None:

    if isinstance(
        value,
        str,
    ):
        return value

    return None
