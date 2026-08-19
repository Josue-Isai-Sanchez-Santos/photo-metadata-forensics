# Photo Metadata Forensics

Herramienta educativa y de análisis forense para inspeccionar
metadatos y estructuras internas de archivos de imagen.

## Estado actual

Versión inicial en desarrollo.

Actualmente puede:

- Validar la firma básica de archivos JPEG.
- Recorrer segmentos JPEG antes de los datos comprimidos.
- Mostrar marcadores y offsets.
- Detectar segmentos APP1.
- Identificar un payload EXIF mediante `Exif\0\0`.

## Objetivo

El proyecto evolucionará hacia una herramienta capaz de:

- Extraer metadatos EXIF.
- Analizar información TIFF/IFD.
- Extraer información GPS.
- Detectar datos potencialmente sensibles.
- Comparar metadatos entre imágenes.
- Calcular hashes.
- Generar reportes.
- Eliminar metadatos de copias sanitizadas.
- Analizar directorios completos.

## Filosofía del proyecto

Las primeras versiones implementan manualmente parte del parsing
binario para comprender la estructura interna de JPEG, TIFF y EXIF.

Posteriormente podrán incorporarse herramientas maduras como
ExifTool para ampliar cobertura y compatibilidad.

## Aviso

La presencia, ausencia o modificación de metadatos no demuestra por
sí sola la autenticidad o falsedad de una imagen.
