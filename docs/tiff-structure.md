# TIFF Structure in PhotoMeta

## 1. Purpose

This document describes the TIFF structures implemented by PhotoMeta.

TIFF is important to this project because JPEG EXIF metadata embeds a TIFF
structure inside an APP1 segment.

PhotoMeta implements the relevant TIFF parsing directly in Python so the
project can expose and validate the underlying binary representation rather
than treating EXIF as an opaque metadata dictionary.


## 2. TIFF inside PhotoMeta

In a JPEG EXIF segment, the simplified structure is:

    JPEG APP1
    |
    +-- Exif\0\0
        |
        +-- TIFF header
        |
        +-- IFD0
        |    |
        |    +-- TIFF tags
        |    +-- ExifIFDPointer
        |    +-- GPSInfoIFDPointer
        |
        +-- ExifIFD
        |
        +-- GPS IFD
        |
        +-- external TIFF values

TIFF offsets used by PhotoMeta are interpreted relative to the beginning of
the TIFF structure, not relative to the beginning of the JPEG file.


## 3. TIFF header

PhotoMeta expects the TIFF header to occupy at least eight bytes:

    Offset   Size   Meaning
    ------   ----   -------------------------
    0        2      Byte-order marker
    2        2      TIFF magic number
    4        4      Offset to first IFD

Conceptually:

    +0   Byte order
    +2   Magic = 42
    +4   First IFD offset


## 4. Endianness

TIFF can encode multibyte integers in two byte orders.

PhotoMeta supports both:

    II    Little-endian / Intel

    MM    Big-endian / Motorola

The byte-order marker controls how subsequent TIFF integers are decoded.

For example, decimal value 42 can appear as:

    Little-endian:
        2A 00

    Big-endian:
        00 2A

PhotoMeta does not assume one order globally. The order is read from the
TIFF header and then propagated when decoding IFD entries, offsets and
values.


## 5. TIFF magic number

Bytes 2-3 of the TIFF header must decode to:

    42

using the selected TIFF byte order.

PhotoMeta rejects a TIFF structure when this value is not 42.

The value 42 is a structural TIFF signature. It is not an image width,
version number or metadata tag.


## 6. Offset to the first IFD

Bytes 4-7 contain a 32-bit offset to the first Image File Directory.

In normal EXIF data this first directory is IFD0.

The offset is relative to:

    byte 0 of the TIFF structure

not:

    byte 0 of the JPEG

and not:

    byte 0 of APP1

This distinction is fundamental when manually inspecting EXIF bytes.


## 7. TIFF offsets

PhotoMeta treats offsets as untrusted values.

Before following an offset it verifies that the requested byte range exists
within the TIFF data.

A structurally valid offset must not point:

- before the supported TIFF structure
- beyond the available TIFF bytes
- to a range that would extend beyond the available data

Guarded IFD traversal also rejects repeated offsets in order to prevent
circular structures.


## 8. TIFF field types supported by PhotoMeta

PhotoMeta currently implements TIFF field types 1 through 12.

| ID | Type | Bytes per component | PhotoMeta result |
| ---: | --- | ---: | --- |
| 1 | BYTE | 1 | integer or tuple |
| 2 | ASCII | 1 | string |
| 3 | SHORT | 2 | unsigned integer or tuple |
| 4 | LONG | 4 | unsigned integer or tuple |
| 5 | RATIONAL | 8 | Fraction or tuple |
| 6 | SBYTE | 1 | signed integer or tuple |
| 7 | UNDEFINED | 1 | bytes |
| 8 | SSHORT | 2 | signed integer or tuple |
| 9 | SLONG | 4 | signed integer or tuple |
| 10 | SRATIONAL | 8 | signed Fraction or tuple |
| 11 | FLOAT | 4 | float or tuple |
| 12 | DOUBLE | 8 | float or tuple |

The total byte size of a TIFF value is:

    component_size * count


## 9. Count

Each IFD entry contains a 32-bit `count`.

Count specifies how many components of the declared TIFF type belong to the
value.

Examples:

    Type = SHORT
    Count = 1

    total size = 2 bytes


    Type = RATIONAL
    Count = 3

    total size = 24 bytes


    Type = ASCII
    Count = 12

    total size = 12 bytes

PhotoMeta validates count before allocating or iterating over a value.


## 10. Value versus offset

Every TIFF IFD entry reserves exactly four bytes for a field called
Value/Offset.

The meaning depends on the complete size of the value.

If:

    value_size <= 4 bytes

the value itself is stored directly in those four bytes.

If:

    value_size > 4 bytes

those four bytes contain an offset to the real value.

PhotoMeta implements this distinction explicitly.


### Example: inline SHORT

    Type:
        SHORT

    Count:
        1

    Size:
        2 bytes

Because the value needs only two bytes, it fits inside Value/Offset.


### Example: external ASCII

    Type:
        ASCII

    Count:
        20

    Size:
        20 bytes

Twenty bytes cannot fit inside the four-byte Value/Offset field.

Therefore Value/Offset contains a 32-bit offset pointing to those twenty
bytes elsewhere in the TIFF structure.


## 11. RATIONAL

TIFF RATIONAL occupies eight bytes:

    numerator      4 bytes
    denominator    4 bytes

PhotoMeta preserves the exact ratio using Python `Fraction`.

For example:

    1 / 250

can represent an exposure time without immediately losing precision through
floating-point conversion.

A denominator of zero is rejected.


## 12. SRATIONAL

SRATIONAL has the same eight-byte layout but allows signed numerator and
denominator values.

PhotoMeta also represents these values using `Fraction`.


## 13. ASCII

TIFF ASCII values are decoded as ASCII text.

Trailing NUL bytes are removed before decoding.

If a value is declared as ASCII but contains invalid non-ASCII bytes,
PhotoMeta reports a TIFF parsing error rather than silently inventing a
replacement string.


## 14. UNDEFINED

TIFF type UNDEFINED is preserved as raw bytes.

PhotoMeta does not guess an interpretation for arbitrary UNDEFINED data.

This is especially important for manufacturer-specific fields such as some
MakerNote structures.


## 15. Scalar versus multiple components

PhotoMeta generally represents:

    Count = 1

as a scalar value.

Multiple numeric components are returned as tuples.

Exceptions include:

    ASCII      -> string
    UNDEFINED  -> bytes


## 16. TIFF and EXIF

TIFF itself defines the binary directory mechanism.

EXIF builds on that mechanism by assigning photographic meanings to
particular tags and by using additional directories such as:

    IFD0
    ExifIFD
    GPS IFD

For the EXIF-specific layer see:

    docs/exif.md

For IFD internals see:

    docs/ifd.md

For supported tag names see:

    docs/exif-tags.md


## 17. Security

TIFF fields are attacker-controlled when PhotoMeta analyzes an unknown
image.

The parser therefore validates:

- IFD offsets
- number of IFD entries
- component counts
- decoded value sizes
- external value ranges
- next-IFD offsets
- traversal depth
- total IFD nodes
- repeated/circular IFD offsets

See:

    docs/parser-security.md

for the current defensive limits.


## 18. Relevant implementation

    photometa/parsers/tiff.py
    photometa/parsers/exif.py
    photometa/extractors/ifd0.py
    photometa/extractors/exif_ifd.py
    photometa/extractors/gps_ifd.py

Relevant tests include:

    tests/test_tiff.py
    tests/test_exif.py
    tests/test_ifd0.py
    tests/test_exif_ifd.py
    tests/test_gps_ifd.py
    tests/test_parser_security.py


## 19. Scope

This document describes the TIFF behavior implemented by PhotoMeta.

It is not a complete TIFF specification.

PhotoMeta currently focuses on the TIFF structures necessary for its image
metadata and EXIF analysis features.
