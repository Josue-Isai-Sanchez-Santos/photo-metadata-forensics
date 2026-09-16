# Supported Image Formats

PhotoMeta has different support levels depending on format and backend.

## JPEG

Support level:

    FULL native metadata/forensic path

Features include:

- native marker parser
- EXIF/TIFF/IFD
- GPS
- XMP
- ICC
- IPTC
- privacy analysis
- anomaly analysis
- comparison
- sanitization
- JSON
- HTML report
- batch processing

## PNG

Backend:

    Pillow

Support level:

    basic inspection

Includes dimensions, mode, frames, hashes and selected metadata-presence
information when exposed by Pillow.

## WebP

Backend:

    Pillow

Support level:

    basic inspection

Animated images can be identified.

## TIFF

Standalone TIFF scanning uses the Pillow additional-format path.

This should not be confused with PhotoMeta's native TIFF parser used for
TIFF structures embedded inside JPEG EXIF.

## HEIC / HEIF

Backend:

    pillow-heif

Installation:

    python -m pip install -e ".[heif]"

PhotoMeta detects supported ISO-BMFF HEIF brands and deliberately avoids
treating AVIF as HEIF merely because compatible brands overlap.

Support is basic metadata/container inspection, not equivalent to the full
native JPEG path.

## RAW

Backend:

    rawpy / LibRaw

Installation:

    python -m pip install -e ".[raw]"

Candidate extensions include common DNG, NEF, CR2, CR3, ARW, RAF, ORF,
RW2 and other RAW formats.

Extension matching is only a candidate filter.

LibRaw performs actual validation.

PhotoMeta does not call RAW postprocessing merely to validate a file.

## ExifTool compatibility path

ExifTool can inspect a single file when selected explicitly:

    photometa scan FILE --backend exiftool

It is an optional compatibility backend, not a replacement for the native
parser and not an authenticity oracle.

## Important support distinction

`supported` does not mean that every metadata feature is implemented for
every format.

In particular, privacy, scrub, anomaly and detailed comparison operations
currently focus on JPEG.
