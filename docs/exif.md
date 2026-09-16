# EXIF in PhotoMeta

## 1. Purpose

PhotoMeta implements native EXIF parsing for JPEG images.

The implementation is educational and forensic: it exposes the actual JPEG,
TIFF and IFD structures instead of depending exclusively on a high-level
metadata library.


## 2. EXIF inside JPEG

PhotoMeta looks for a JPEG APP1 segment:

    FF E1

whose payload begins with:

    Exif\0\0

Simplified layout:

    JPEG
    |
    +-- APP1
        |
        +-- Exif\0\0
            |
            +-- TIFF header
            |
            +-- IFD0
            |    |
            |    +-- ExifIFDPointer
            |    +-- GPSInfoIFDPointer
            |
            +-- ExifIFD
            |
            +-- GPS IFD


## 3. EXIF identifier

PhotoMeta distinguishes EXIF from other APP1 content using the six-byte
identifier:

    Exif\0\0

APP1 by itself does not mean EXIF.

The same JPEG marker can also contain other metadata such as XMP.


## 4. Extracting TIFF

Once the EXIF identifier is validated, PhotoMeta removes those six identifier
bytes from the interpretation layer.

The remaining payload is processed as TIFF data.

TIFF offset zero therefore means:

    beginning of the embedded TIFF structure

and not:

    beginning of APP1

or:

    beginning of the JPEG file


## 5. TIFF header

The EXIF TIFF header provides:

    byte order
    magic number
    first IFD offset

PhotoMeta supports:

    II / little-endian
    MM / big-endian

and requires TIFF magic number:

    42


## 6. IFD0

The first IFD parsed by PhotoMeta is IFD0.

IFD0 can contain general image/device metadata including:

    Make
    Model
    Orientation
    Software
    DateTime
    Artist
    Copyright

Two particularly important fields are:

    0x8769 ExifIFDPointer
    0x8825 GPSInfoIFDPointer


## 7. ExifIFD

PhotoMeta follows `ExifIFDPointer` to parse the ExifIFD.

Supported tag names include information related to:

- exposure
- aperture
- ISO / sensitivity
- capture date
- metering
- flash
- focal length
- color space
- pixel dimensions
- white balance
- scene capture type
- camera owner
- body serial number
- lens information
- image unique ID

See:

    docs/exif-tags.md

for the exact tag table currently implemented.


## 8. Capture summary

The higher-level ExifIFD extractor can build a human-readable capture
summary containing:

    date
    time
    exposure
    ISO
    aperture
    focal length
    lens

This presentation layer is separate from raw TIFF decoding.


## 9. ISO handling

PhotoMeta checks several supported sensitivity fields when producing its
summary:

    PhotographicSensitivity
    ISOSpeed
    StandardOutputSensitivity
    RecommendedExposureIndex

This allows the presentation layer to work with more than one EXIF
sensitivity representation.


## 10. Exposure and aperture

Exact RATIONAL values remain `Fraction` values in the TIFF layer.

The presentation layer may render them as friendly values such as:

    1/250 s
    f/2.8
    35 mm

The formatted value is not a replacement for the underlying rational value.


## 11. DateTimeOriginal

`DateTimeOriginal` is interpreted using the common EXIF format:

    YYYY:MM:DD HH:MM:SS

PhotoMeta can split it into display date and time.

The base field itself does not automatically establish a timezone.


## 12. GPS IFD

PhotoMeta follows `GPSInfoIFDPointer` from IFD0.

Supported GPS fields include:

    GPSLatitudeRef
    GPSLatitude
    GPSLongitudeRef
    GPSLongitude
    GPSAltitudeRef
    GPSAltitude
    GPSTimeStamp
    GPSImgDirection
    GPSDateStamp

as well as additional GPS tags listed in `docs/exif-tags.md`.


## 13. GPS coordinates

EXIF GPS latitude and longitude are commonly encoded as three RATIONAL
components:

    degrees
    minutes
    seconds

with a separate reference:

    N
    S
    E
    W

PhotoMeta converts them using:

    decimal =
        degrees
        + minutes / 60
        + seconds / 3600

South and West produce negative decimal coordinates.


## 14. GPS altitude reference

PhotoMeta currently interprets GPSAltitudeRef values as:

    0   positive ellipsoidal height
    1   negative ellipsoidal height
    2   positive sea-level altitude
    3   negative sea-level altitude

The distinction matters.

A negative ellipsoidal height must not automatically be described as an
altitude below mean sea level.


## 15. MakerNote

PhotoMeta recognizes the ExifIFD tag:

    0x927C MakerNote

but does not claim to generically decode manufacturer-specific MakerNote
formats.

Such data can be proprietary and camera-vendor dependent.


## 16. Unknown EXIF tags

Unknown ExifIFD tags are preserved structurally and assigned a generated
name:

    UnknownExifTag_XXXX

This is preferable to silently dropping information simply because the
current project does not have a friendly label for it.


## 17. EXIF and privacy

EXIF can contain privacy-relevant information such as:

- exact GPS position
- capture date/time
- camera model
- camera owner name
- body serial number
- lens serial number
- unique image identifiers

Presence of such metadata means that the information exists in the file.

It does not by itself mean the file is malicious or manipulated.


## 18. EXIF and forensic interpretation

Metadata can be useful evidence when comparing or inspecting files, but
PhotoMeta deliberately avoids treating EXIF as proof of authenticity.

Metadata can be:

- removed
- rewritten
- incomplete
- absent from the original capture
- modified by software
- copied between files

Therefore:

    EXIF present != authentic

    EXIF absent != manipulated


## 19. Sanitization

PhotoMeta can remove complete EXIF APP1 metadata during full sanitization.

Selective sanitization can instead target supported privacy-sensitive fields
while attempting to preserve unrelated metadata.


## 20. Parser safety

EXIF metadata is treated as untrusted binary input.

Defensive parsing covers:

- TIFF byte order
- magic number
- offsets
- IFD entry counts
- external value ranges
- component counts
- value sizes
- circular/repeated IFD pointers
- traversal depth
- traversal node count

See:

    docs/parser-security.md


## 21. Relevant implementation

    photometa/parsers/exif.py
    photometa/parsers/tiff.py
    photometa/parsers/tags.py
    photometa/extractors/ifd0.py
    photometa/extractors/exif_ifd.py
    photometa/extractors/gps_ifd.py


## 22. Related documentation

    docs/jpeg-structure.md
    docs/tiff-structure.md
    docs/ifd.md
    docs/exif-tags.md
    docs/parser-security.md


## 23. Scope

PhotoMeta does not claim complete implementation of every EXIF revision,
manufacturer extension or MakerNote format.

This document describes the native EXIF structures and tags currently
implemented by this repository.
