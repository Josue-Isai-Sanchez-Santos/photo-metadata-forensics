from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from photometa.parsers.exif import (
    ExifData,
    parse_exif,
)
from photometa.parsers.jpeg import (
    iter_jpeg_segments,
)
from photometa.parsers.tags import (
    get_tiff_tag_name,
)
from photometa.parsers.tiff import (
    DecodedTiffValue,
    decode_ifd_value,
)


class Ifd0ExtractorError(Exception):
    """Base exception for IFD0 extraction errors."""


@dataclass(frozen=True)
class Ifd0MetadataEntry:
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
class Ifd0Metadata:
    entries: tuple[Ifd0MetadataEntry, ...]

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


def extract_ifd0_metadata(
    exif: ExifData,
) -> Ifd0Metadata:
    """
    Decodifica todas las entradas presentes
    en IFD0.
    """

    decoded_entries: list[
        Ifd0MetadataEntry
    ] = []

    for entry in exif.ifd0.entries:
        value = decode_ifd_value(
            exif.tiff_data,
            entry,
            exif.header.byte_order,
        )

        decoded_entries.append(
            Ifd0MetadataEntry(
                tag=entry.tag,
                tag_name=get_tiff_tag_name(
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

    return Ifd0Metadata(
        entries=tuple(
            decoded_entries
        )
    )


def extract_ifd0_from_jpeg(
    path: str | Path,
) -> Ifd0Metadata:
    """
    Localiza el primer APP1 EXIF de un JPEG
    y devuelve los metadatos de su IFD0.
    """

    segments = iter_jpeg_segments(
        path
    )

    exif_segment = next(
        (
            segment
            for segment in segments
            if segment.is_exif
        ),
        None,
    )

    if exif_segment is None:
        raise Ifd0ExtractorError(
            "No se encontró un segmento APP1 "
            "con metadatos EXIF."
        )

    exif = parse_exif(
        exif_segment
    )

    return extract_ifd0_metadata(
        exif
    )
