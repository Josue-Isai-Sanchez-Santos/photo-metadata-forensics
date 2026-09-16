# PhotoMeta Architecture

## Overview

PhotoMeta separates low-level binary parsing from extraction,
interpretation, analysis, presentation, export and sanitization.

A simplified flow is:

    image file
        |
        v
    format detection
        |
        +-- native JPEG parser
        |       |
        |       +-- EXIF / TIFF / IFD
        |       +-- XMP
        |       +-- ICC
        |       +-- IPTC
        |
        +-- Pillow backend
        +-- HEIF backend
        +-- RAW backend
        +-- optional ExifTool backend
        |
        v
    analysis
        |
        +-- privacy
        +-- comparison
        +-- anomalies
        +-- batch
        |
        v
    presentation / export / sanitization

## Main packages

### `photometa/parsers`

Contains native binary and metadata parsers:

    jpeg.py
    tiff.py
    exif.py
    tags.py
    xmp.py
    icc.py
    iptc.py
    limits.py

These modules operate close to the source bytes.

### `photometa/extractors`

Converts low-level TIFF structures into metadata groups:

    ifd0.py
    exif_ifd.py
    gps_ifd.py

### `photometa/interpretation`

Adds human-readable interpretations for selected enumerated fields without
changing the underlying parsed values.

### `photometa/analysis`

Higher-level operations:

    privacy.py
    privacy_score.py
    comparison.py
    anomalies.py
    batch.py
    report.py

### `photometa/sanitization`

Rewrites JPEG metadata while preserving compressed image data:

    jpeg_rewriter.py
    scrub.py
    selective.py

### `photometa/formats`

Optional/broader format support:

    pillow_backend.py
    heif_backend.py
    raw_backend.py

### `photometa/backends`

External compatibility backends such as ExifTool.

### `photometa/exporters`

Machine-readable and standalone outputs:

    json_export.py
    csv_export.py
    html_report.py

### `photometa/presentation`

Human-readable CLI formatting.

## Design principles

PhotoMeta attempts to keep these concepts separate:

    raw bytes
    parsed structure
    decoded metadata
    human interpretation
    forensic heuristic
    privacy assessment

This matters because an interpretation should never silently replace the
underlying evidence.

## Native JPEG path

The native JPEG implementation is intentionally independent of Pillow for
structural parsing.

It supports:

- marker inspection
- APP metadata discovery
- EXIF/TIFF parsing
- XMP
- ICC
- IPTC
- JPEG coding fingerprints
- scan-data hashing
- metadata sanitization

## Optional backends

Pillow, pillow-heif, rawpy/LibRaw and ExifTool expand compatibility.

They do not replace the educational native JPEG parser.

## CLI

`photometa/cli.py` is the main user-facing orchestration layer.

It delegates work to the analysis, parser, exporter and sanitization
packages rather than implementing those operations itself.
