from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    get_exif_tag_name,
)
from photometa.parsers.tiff import (
    DecodedTiffValue,
    Ifd,
    IfdTraversalState,
    decode_ifd_value,
    parse_ifd_guarded,
)


EXIF_IFD_POINTER_TAG = 0x8769


class ExifIfdExtractorError(Exception):
    """Base exception for ExifIFD extraction errors."""


@dataclass(frozen=True)
class ExifIfdMetadataEntry:
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
class ExifIfdMetadata:
    offset: int
    entries: tuple[ExifIfdMetadataEntry, ...]

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

    def get_iso(
        self,
    ) -> int | None:
        """
        Devuelve una sensibilidad ISO utilizable.

        PhotographicSensitivity (0x8827) es habitual
        en fotografías existentes.

        ISOSpeed (0x8833) es otro campo definido
        en revisiones modernas de Exif.
        """

        for name in (
            "PhotographicSensitivity",
            "ISOSpeed",
            "StandardOutputSensitivity",
            "RecommendedExposureIndex",
        ):
            value = self.get(name)

            if isinstance(value, int):
                return value

        return None


@dataclass(frozen=True)
class CaptureSummary:
    date: str | None
    time: str | None
    exposure: str | None
    iso: int | None
    aperture: str | None
    focal_length: str | None
    lens: str | None


def _get_exif_ifd_pointer(
    exif: ExifData,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> int:

    pointer_entry = next(
        (
            entry
            for entry in exif.ifd0.entries
            if entry.tag == EXIF_IFD_POINTER_TAG
        ),
        None,
    )

    if pointer_entry is None:
        raise ExifIfdExtractorError(
            "IFD0 no contiene ExifIFDPointer."
        )

    value = decode_ifd_value(
        exif.tiff_data,
        pointer_entry,
        exif.header.byte_order,
        limits=limits,
    )

    if not isinstance(value, int):
        raise ExifIfdExtractorError(
            "ExifIFDPointer no contiene "
            "un offset entero válido."
        )

    if value <= 0:
        raise ExifIfdExtractorError(
            f"ExifIFDPointer inválido: {value}."
        )

    return value


def parse_exif_ifd(
    exif: ExifData,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> Ifd:
    """
    Sigue ExifIFDPointer desde IFD0.
    """

    offset = _get_exif_ifd_pointer(
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


def extract_exif_ifd_metadata(
    exif: ExifData,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> ExifIfdMetadata:
    """
    Decodifica las entradas del ExifIFD.
    """

    exif_ifd = parse_exif_ifd(
        exif,
        limits=limits,
    )

    entries: list[
        ExifIfdMetadataEntry
    ] = []

    for entry in exif_ifd.entries:

        value = decode_ifd_value(
            exif.tiff_data,
            entry,
            exif.header.byte_order,
            limits=limits,
        )

        entries.append(
            ExifIfdMetadataEntry(
                tag=entry.tag,
                tag_name=get_exif_tag_name(
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

    return ExifIfdMetadata(
        offset=exif_ifd.offset,
        entries=tuple(entries),
    )


def extract_exif_ifd_from_jpeg(
    path: str | Path,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> ExifIfdMetadata:
    """
    Extrae ExifIFD directamente desde un JPEG.
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
        raise ExifIfdExtractorError(
            "No se encontró un segmento "
            "APP1 EXIF."
        )

    exif = parse_exif(
        exif_segment,
        limits=limits,
    )

    return extract_exif_ifd_metadata(
        exif,
        limits=limits,
    )


def build_capture_summary(
    metadata: ExifIfdMetadata,
) -> CaptureSummary:
    """
    Construye una vista amigable de los
    principales datos de captura.

    No interpreta todavía campos APEX como
    ShutterSpeedValue o ApertureValue.
    """

    date, time = _split_exif_datetime(
        metadata.get(
            "DateTimeOriginal"
        )
    )

    exposure = _format_exposure(
        metadata.get(
            "ExposureTime"
        )
    )

    aperture = _format_aperture(
        metadata.get(
            "FNumber"
        )
    )

    focal_length = _format_focal_length(
        metadata.get(
            "FocalLength"
        )
    )

    lens = _format_lens(
        metadata.get("LensMake"),
        metadata.get("LensModel"),
    )

    return CaptureSummary(
        date=date,
        time=time,
        exposure=exposure,
        iso=metadata.get_iso(),
        aperture=aperture,
        focal_length=focal_length,
        lens=lens,
    )


def _split_exif_datetime(
    value: object,
) -> tuple[str | None, str | None]:

    if not isinstance(value, str):
        return None, None

    try:
        parsed = datetime.strptime(
            value,
            "%Y:%m:%d %H:%M:%S",
        )

    except ValueError:
        return value, None

    return (
        parsed.strftime("%Y-%m-%d"),
        parsed.strftime("%H:%M:%S"),
    )


def _format_exposure(
    value: object,
) -> str | None:

    if isinstance(value, Fraction):

        if value <= 0:
            return None

        if value < 1:

            denominator = round(
                1 / float(value)
            )

            if denominator > 0:
                return (
                    f"1/{denominator} s"
                )

        return (
            f"{float(value):g} s"
        )

    if isinstance(value, int):

        if value <= 0:
            return None

        return f"{value} s"

    return None


def _format_aperture(
    value: object,
) -> str | None:

    if isinstance(value, (Fraction, int)):
        number = float(value)

        return f"f/{number:g}"

    return None


def _format_focal_length(
    value: object,
) -> str | None:

    if isinstance(value, (Fraction, int)):
        number = float(value)

        return f"{number:g} mm"

    return None


def _format_lens(
    make: object,
    model: object,
) -> str | None:

    make_text = (
        make
        if isinstance(make, str)
        else None
    )

    model_text = (
        model
        if isinstance(model, str)
        else None
    )

    if model_text and make_text:

        if model_text.lower().startswith(
            make_text.lower()
        ):
            return model_text

        return f"{make_text} {model_text}"

    if model_text:
        return model_text

    if make_text:
        return make_text

    return None
