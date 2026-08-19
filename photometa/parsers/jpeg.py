from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator


class JpegParserError(Exception):
    """Base exception for JPEG parsing errors."""


@dataclass(frozen=True)
class JpegSegment:
    offset: int
    marker: int
    name: str
    declared_length: int | None = None
    payload_length: int = 0
    is_exif: bool = False

    @property
    def marker_hex(self) -> str:
        return f"FF{self.marker:02X}"


MARKER_NAMES: dict[int, str] = {
    0x01: "TEM",

    0xC0: "SOF0",
    0xC1: "SOF1",
    0xC2: "SOF2",
    0xC4: "DHT",
    0xC5: "SOF5",
    0xC6: "SOF6",
    0xC7: "SOF7",
    0xC8: "JPG",
    0xC9: "SOF9",
    0xCA: "SOF10",
    0xCB: "SOF11",
    0xCC: "DAC",
    0xCD: "SOF13",
    0xCE: "SOF14",
    0xCF: "SOF15",

    0xD8: "SOI",
    0xD9: "EOI",
    0xDA: "SOS",
    0xDB: "DQT",
    0xDC: "DNL",
    0xDD: "DRI",
    0xDE: "DHP",
    0xDF: "EXP",

    0xFE: "COM",
}


for i in range(8):
    MARKER_NAMES[0xD0 + i] = f"RST{i}"


for i in range(16):
    MARKER_NAMES[0xE0 + i] = f"APP{i}"


STANDALONE_MARKERS = {
    0x01,                  # TEM
    0xD8,                  # SOI
    0xD9,                  # EOI
    *range(0xD0, 0xD8),   # RST0-RST7
}


def _read_exact(
    file: BinaryIO,
    size: int,
    context: str,
) -> bytes:
    data = file.read(size)

    if len(data) != size:
        raise JpegParserError(
            f"Archivo truncado mientras se leía {context}: "
            f"se esperaban {size} bytes y se obtuvieron {len(data)}."
        )

    return data


def _read_marker_code(file: BinaryIO) -> tuple[int, int]:
    """
    Lee el siguiente marcador JPEG fuera de los datos
    comprimidos de imagen.

    Devuelve:
        (offset, marker_code)
    """

    first = file.read(1)

    if not first:
        raise JpegParserError(
            "Fin de archivo inesperado antes de encontrar EOI/SOS."
        )

    if first != b"\xFF":
        raise JpegParserError(
            f"Se esperaba prefijo de marcador FF en offset "
            f"0x{file.tell() - 1:08X}, "
            f"pero se encontró {first.hex().upper()}."
        )

    marker_offset = file.tell() - 1

    code = _read_exact(
        file,
        1,
        "código de marcador",
    )

    # Pueden existir bytes FF de relleno antes del
    # código real del marcador.
    while code == b"\xFF":
        code = _read_exact(
            file,
            1,
            "byte de relleno de marcador",
        )

    if code == b"\x00":
        raise JpegParserError(
            f"Se encontró FF00 fuera de los datos comprimidos "
            f"en offset 0x{marker_offset:08X}."
        )

    return marker_offset, code[0]


def iter_jpeg_segments(
    path: str | Path,
) -> Iterator[JpegSegment]:

    image_path = Path(path)

    with image_path.open("rb") as file:

        signature = _read_exact(
            file,
            2,
            "firma JPEG",
        )

        if signature != b"\xFF\xD8":
            raise JpegParserError(
                "El archivo no comienza con FF D8 (SOI); "
                "no parece ser un JPEG válido."
            )

        yield JpegSegment(
            offset=0,
            marker=0xD8,
            name="SOI",
        )

        while True:

            offset, marker = _read_marker_code(file)

            name = MARKER_NAMES.get(
                marker,
                f"UNKNOWN_{marker:02X}",
            )

            if marker in STANDALONE_MARKERS:

                yield JpegSegment(
                    offset=offset,
                    marker=marker,
                    name=name,
                )

                if marker == 0xD9:
                    return

                continue

            length_bytes = _read_exact(
                file,
                2,
                f"longitud de {name}",
            )

            declared_length = int.from_bytes(
                length_bytes,
                byteorder="big",
            )

            if declared_length < 2:
                raise JpegParserError(
                    f"Longitud inválida ({declared_length}) "
                    f"para {name} "
                    f"en offset 0x{offset:08X}."
                )

            payload_length = declared_length - 2

            payload = _read_exact(
                file,
                payload_length,
                f"payload de {name}",
            )

            is_exif = (
                marker == 0xE1
                and payload.startswith(b"Exif\x00\x00")
            )

            yield JpegSegment(
                offset=offset,
                marker=marker,
                name=name,
                declared_length=declared_length,
                payload_length=payload_length,
                is_exif=is_exif,
            )

            #
            # V0:
            #
            # Después de SOS comienzan los datos comprimidos.
            # Todavía no intentaremos recorrer esa región.
            #
            if marker == 0xDA:
                return
