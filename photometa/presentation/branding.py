from __future__ import annotations

PRODUCT_NAME = (
    "PHOTO METADATA FORENSICS"
)


PRODUCT_TAGLINE = (
    "Image Metadata • Privacy • "
    "Forensic Analysis"
)


MAIN_BANNER = """\
╭────────────────────────────────────────────────────╮
│ PHOTO METADATA FORENSICS                           │
│ Image Metadata • Privacy • Forensic Analysis       │
╰────────────────────────────────────────────────────╯
"""


MAIN_HELP_EPILOG = """\
Quick examples:

  # Ver todos los metadatos
  photometa scan foto.jpg

  # Mostrar únicamente datos sensibles
  photometa privacy foto.jpg

  # Extraer GPS
  photometa gps foto.jpg

  # Procesar una carpeta
  photometa scan ./imagenes/

  # Procesar carpetas recursivamente
  photometa scan ./imagenes/ --recursive

  # Generar JSON
  photometa scan foto.jpg --json

  # Crear reporte HTML
  photometa report foto.jpg --output report.html

  # Crear una copia sin metadatos
  photometa scrub foto.jpg --output foto_clean.jpg

  # Comparar dos imágenes
  photometa compare original.jpg copia.jpg

Documentation:
  https://github.com/Josue-Isai-Sanchez-Santos/photo-metadata-forensics/blob/main/docs/index.md
"""


def format_main_description() -> str:
    return (
        MAIN_BANNER
        + "\n"
        + (
            "Inspect image metadata, "
            "privacy exposure and "
            "forensic structure."
        )
    )
