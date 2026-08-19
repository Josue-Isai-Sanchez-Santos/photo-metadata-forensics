from __future__ import annotations

import argparse
import sys
from pathlib import Path

from photometa.parsers.jpeg import (
    JpegParserError,
    iter_jpeg_segments,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photometa",
        description=(
            "Inspecciona la estructura de segmentos "
            "de un archivo JPEG."
        ),
    )

    parser.add_argument(
        "image",
        type=Path,
        help="Ruta de la imagen JPEG",
    )

    return parser


def main() -> int:

    args = build_parser().parse_args()

    if not args.image.is_file():
        print(
            f"Error: no existe el archivo: {args.image}",
            file=sys.stderr,
        )
        return 2

    try:
        segments = list(
            iter_jpeg_segments(args.image)
        )

    except (OSError, JpegParserError) as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"Archivo: {args.image}")
    print()

    print(
        f"{'OFFSET':<12} "
        f"{'MARKER':<8} "
        f"{'TIPO':<10} "
        f"{'LONGITUD':<10} "
        f"DETALLE"
    )

    print("-" * 62)

    for segment in segments:

        if segment.declared_length is None:
            length = "-"
        else:
            length = str(segment.declared_length)

        detail = (
            "EXIF detectado"
            if segment.is_exif
            else ""
        )

        print(
            f"0x{segment.offset:08X} "
            f"{segment.marker_hex:<8} "
            f"{segment.name:<10} "
            f"{length:<10} "
            f"{detail}"
        )

    print()

    if any(
        segment.is_exif
        for segment in segments
    ):
        print(
            "Resultado: se encontró un segmento "
            "APP1 con identificador Exif."
        )

    else:
        print(
            "Resultado: no se encontró EXIF "
            "antes del primer SOS."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
