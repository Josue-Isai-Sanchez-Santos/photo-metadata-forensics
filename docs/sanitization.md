# JPEG Metadata Sanitization

## Purpose

PhotoMeta creates sanitized JPEG copies without intentionally decoding and
re-encoding compressed image data.

The original input file is not modified in place.

## Full scrub

    photometa scrub image.jpg

Equivalent explicit mode:

    photometa scrub image.jpg --all

Typical removable metadata includes:

- EXIF APP1
- XMP APP1
- Photoshop/APP13 metadata
- generic application metadata
- JPEG comments

Technical structures normally preserved include:

- JFIF / JFXX APP0
- ICC APP2
- recognized Adobe APP14 technical data

## GPS-only scrub

    photometa scrub image.jpg --gps

Removes supported GPS metadata while attempting to preserve unrelated
metadata.

## Privacy scrub

    photometa scrub image.jpg --privacy

Removes supported privacy-sensitive information from EXIF, XMP and IPTC
while preserving unrelated supported metadata.

Examples include:

- camera model
- software
- artist
- copyright
- DateTimeOriginal
- ImageUniqueID
- CameraOwnerName
- BodySerialNumber
- LensSerialNumber
- selected XMP identifiers/location fields
- selected IPTC creator/date/location fields

## Verification

Sanitization reports can compare:

- original hash before and after
- output hash
- dimensions
- compressed scan-data hash
- GPS before/after
- privacy findings before/after
- removed/modified segments

Equal scan-data hashes support that compressed JPEG scan bytes were
preserved.

They do not prove that two files decode to identical pixels under every
possible decoder or coding-table configuration.

## Safety

The scrubber refuses destructive in-place rewriting and uses controlled
output handling.
