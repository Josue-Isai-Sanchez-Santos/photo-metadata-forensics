from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from photometa.hashing import (
    calculate_sha256,
)
from photometa.parsers.jpeg import (
    JpegParserError,
    iter_jpeg_segments,
)


class FileInfoError(Exception):
    """Base exception for file information errors."""


JPEG_SOF_MARKERS = {
    0xC0,  # SOF0
    0xC1,  # SOF1
    0xC2,  # SOF2
    0xC3,  # SOF3
    0xC5,  # SOF5
    0xC6,  # SOF6
    0xC7,  # SOF7
    0xC9,  # SOF9
    0xCA,  # SOF10
    0xCB,  # SOF11
    0xCD,  # SOF13
    0xCE,  # SOF14
    0xCF,  # SOF15
}


@dataclass(frozen=True)
class FileInfo:
    path: Path
    name: str
    extension: str
    file_type: str
    format: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str

    modified_at: datetime
    accessed_at: datetime

    metadata_changed_at: datetime | None
    created_at: datetime | None

    @property
    def size_human(self) -> str:
        return format_file_size(
            self.size_bytes
        )

    @property
    def resolution(self) -> str:
        return (
            f"{self.width} × "
            f"{self.height}"
        )


def analyze_file(
    path: str | Path,
) -> FileInfo:
    """
    Analiza información general del archivo.

    Importante:
    Los timestamps del sistema de archivos
    NO equivalen a DateTimeOriginal EXIF.
    """

    file_path = Path(path)

    if not file_path.exists():
        raise FileInfoError(
            f"El archivo no existe: {file_path}"
        )

    if not file_path.is_file():
        raise FileInfoError(
            f"La ruta no es un archivo: {file_path}"
        )

    #
    # Tomamos stat antes de leer el archivo.
    #
    # En algunos sistemas, leer el archivo
    # puede afectar st_atime.
    #
    stat_result = file_path.stat()

    (
        file_type,
        file_format,
        mime_type,
    ) = detect_file_format(
        file_path
    )

    width, height = (
        get_jpeg_dimensions(
            file_path
        )
    )

    sha256 = calculate_sha256(
        file_path
    )

    modified_at = _timestamp_to_datetime(
        stat_result.st_mtime
    )

    accessed_at = _timestamp_to_datetime(
        stat_result.st_atime
    )

    created_at = _get_creation_time(
        stat_result
    )

    metadata_changed_at = (
        _get_metadata_change_time(
            stat_result
        )
    )

    return FileInfo(
        path=file_path.resolve(),
        name=file_path.name,
        extension=file_path.suffix,
        file_type=file_type,
        format=file_format,
        mime_type=mime_type,
        size_bytes=stat_result.st_size,
        width=width,
        height=height,
        sha256=sha256,
        modified_at=modified_at,
        accessed_at=accessed_at,
        metadata_changed_at=(
            metadata_changed_at
        ),
        created_at=created_at,
    )


def detect_file_format(
    path: str | Path,
) -> tuple[str, str, str]:
    """
    Detecta el formato por contenido,
    no por extensión.

    Actualmente soportamos JPEG.
    """

    file_path = Path(path)

    with file_path.open("rb") as file:
        signature = file.read(16)

    if signature.startswith(
        b"\xFF\xD8"
    ):
        return (
            "Image",
            "JPEG",
            "image/jpeg",
        )

    raise FileInfoError(
        "Formato no soportado o no reconocido."
    )


def get_jpeg_dimensions(
    path: str | Path,
) -> tuple[int, int]:
    """
    Obtiene width/height desde un segmento
    Start Of Frame (SOF) JPEG.

    Payload SOF:
        precision   1 byte
        height      2 bytes big-endian
        width       2 bytes big-endian
    """

    try:

        for segment in iter_jpeg_segments(
            path
        ):

            if (
                segment.marker
                not in JPEG_SOF_MARKERS
            ):
                continue

            if len(segment.payload) < 5:
                raise FileInfoError(
                    "Segmento SOF JPEG truncado."
                )

            height = int.from_bytes(
                segment.payload[1:3],
                byteorder="big",
            )

            width = int.from_bytes(
                segment.payload[3:5],
                byteorder="big",
            )

            if (
                width <= 0
                or height <= 0
            ):
                raise FileInfoError(
                    "Dimensiones JPEG inválidas."
                )

            return width, height

    except JpegParserError as exc:
        raise FileInfoError(
            f"JPEG inválido: {exc}"
        ) from exc

    raise FileInfoError(
        "No se encontró un segmento SOF "
        "con las dimensiones JPEG."
    )


def format_file_size(
    size_bytes: int,
) -> str:
    """
    Devuelve tamaño usando unidades
    decimales: KB, MB, GB.
    """

    if size_bytes < 0:
        raise FileInfoError(
            "El tamaño no puede ser negativo."
        )

    units = (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    )

    size = float(
        size_bytes
    )

    for unit in units:

        if (
            size < 1000
            or unit == units[-1]
        ):

            if unit == "B":
                return (
                    f"{int(size)} B"
                )

            return (
                f"{size:.2f} {unit}"
            )

        size /= 1000

    raise FileInfoError(
        "No se pudo representar "
        "el tamaño del archivo."
    )


def _timestamp_to_datetime(
    timestamp: float,
) -> datetime:

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).astimezone()


def _get_creation_time(
    stat_result: os.stat_result,
) -> datetime | None:
    """
    st_birthtime no está disponible
    en todos los sistemas/filesystems.
    """

    birth_time = getattr(
        stat_result,
        "st_birthtime",
        None,
    )

    if birth_time is not None:
        return _timestamp_to_datetime(
            birth_time
        )

    #
    # Windows moderno expone st_birthtime.
    # Este fallback mantiene compatibilidad
    # con implementaciones anteriores.
    #
    if os.name == "nt":

        return _timestamp_to_datetime(
            stat_result.st_ctime
        )

    return None


def _get_metadata_change_time(
    stat_result: os.stat_result,
) -> datetime | None:
    """
    En Unix/POSIX, st_ctime representa
    cambio de metadatos/inode.

    No debemos llamarlo "creation time".
    """

    if os.name == "nt":
        return None

    return _timestamp_to_datetime(
        stat_result.st_ctime
    )
