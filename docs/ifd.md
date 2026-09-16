# Image File Directories (IFD) in PhotoMeta

## 1. What is an IFD?

An Image File Directory is the central directory structure used by TIFF and
therefore by JPEG EXIF metadata.

An IFD is essentially a table of tagged values.

PhotoMeta represents one parsed directory as:

    Ifd
        offset
        entries
        next_ifd_offset


## 2. Binary layout

The IFD structure implemented by PhotoMeta is:

    2 bytes       number of entries
    N * 12 bytes  IFD entries
    4 bytes       offset of next IFD

Therefore:

    IFD size =
        2
        + (entry_count * 12)
        \+ 4

excluding any external values referenced by its entries.


## 3. IFD entry layout

Every IFD entry occupies exactly 12 bytes:

    Offset   Size   Field
    ------   ----   ----------------
    +0       2      Tag
    +2       2      Field type
    +4       4      Count
    +8       4      Value / Offset


## 4. Tag

The first two bytes identify the meaning of the entry.

Examples used by PhotoMeta include:

    0x010F    Make
    0x0110    Model
    0x0112    Orientation
    0x0132    DateTime
    0x8769    ExifIFDPointer
    0x8825    GPSInfoIFDPointer

A tag ID alone does not contain its value.

The type, count and Value/Offset fields must also be interpreted.


## 5. Field type

The next two bytes identify the TIFF data type.

PhotoMeta currently supports:

    BYTE
    ASCII
    SHORT
    LONG
    RATIONAL
    SBYTE
    UNDEFINED
    SSHORT
    SLONG
    SRATIONAL
    FLOAT
    DOUBLE

Each type has a defined component size.


## 6. Count

Count is a four-byte unsigned integer describing the number of components in
the value.

The complete value size is calculated as:

    size_of(field_type) * count

This result determines whether the value is stored inline or referenced by
offset.


## 7. Value / Offset

The final four bytes have two possible interpretations.

### Inline value

When:

    total_value_size <= 4

the value is stored directly inside the IFD entry.

Example:

    Orientation

    Type:
        SHORT

    Count:
        1

    Total size:
        2 bytes

The value fits inside the four-byte field.


### External value

When:

    total_value_size > 4

the four-byte field is interpreted as an offset from the beginning of the
TIFF data.

Example:

    Model

    Type:
        ASCII

    Count:
        16

Sixteen bytes do not fit inside Value/Offset, so PhotoMeta follows the
stored offset to obtain the string.


## 8. Why the Value/Offset distinction matters

One of the easiest mistakes when implementing TIFF manually is to interpret
all four bytes as an offset.

That would break small values such as many SHORT or LONG fields.

The opposite mistake is also dangerous: interpreting an external offset as
the value itself.

PhotoMeta therefore first calculates the value size and only then decides
how those four bytes must be interpreted.


## 9. IFD0

The first directory reached from the TIFF header is IFD0 in PhotoMeta's
EXIF path.

IFD0 commonly contains image and device information such as:

    ImageWidth
    ImageLength
    Make
    Model
    Orientation
    Software
    DateTime
    Artist
    Copyright

It can also contain pointers to specialized directories:

    ExifIFDPointer
    GPSInfoIFDPointer


## 10. ExifIFDPointer

Tag:

    0x8769

Name:

    ExifIFDPointer

PhotoMeta decodes this IFD0 value as an integer TIFF offset.

The offset is then followed to parse the ExifIFD.

The ExifIFD contains photographic capture metadata such as exposure,
aperture, ISO, focal length and lens information.


## 11. GPSInfoIFDPointer

Tag:

    0x8825

Name:

    GPSInfoIFDPointer

PhotoMeta follows this offset from IFD0 to a GPS-specific IFD.

The GPS directory can contain latitude, longitude, altitude, timestamp,
image direction and related information.


## 12. Next IFD pointer

After all entries, an IFD contains a four-byte `next_ifd_offset`.

Value:

    0

means no next IFD is declared.

A nonzero value is validated as a TIFF offset.

PhotoMeta's current EXIF extraction architecture primarily follows the
explicit ExifIFD and GPSInfoIFD pointers it supports; it does not claim to
implement arbitrary traversal of every TIFF directory graph.


## 13. Guarded traversal

Following attacker-controlled offsets without limits can produce structures
such as:

    IFD A -> IFD A

or:

    IFD A -> IFD B -> IFD A

PhotoMeta uses traversal state containing:

    visited_offsets
    nodes_visited

and applies depth and node budgets.

Revisiting an offset is treated as a circular or repeated pointer.


## 14. Decoding entries

PhotoMeta separates two operations:

    parse_ifd()

parses the directory structure.

    decode_ifd_value()

retrieves and interprets an individual value.

This keeps structural parsing separate from semantic interpretation.


## 15. Raw and interpreted representations

At the low level, PhotoMeta preserves:

    numeric tag
    field type
    count
    raw Value/Offset bytes

Higher-level extractors add:

    tag name
    decoded value
    human-readable summaries

This separation is deliberate.

It allows forensic output to retain the original structural information
while still providing usable metadata to higher-level commands.


## 16. Unknown tags

PhotoMeta does not discard an entry merely because its numeric tag is not in
the current name table.

Unknown entries receive generated names such as:

    UnknownTag_XXXX
    UnknownExifTag_XXXX
    UnknownGpsTag_XXXX

This prevents the tag-name database from becoming a requirement for parsing
the underlying TIFF structure.


## 17. Security considerations

Before accepting an IFD PhotoMeta validates:

- IFD starts after the TIFF header
- entry-count table fits in available bytes
- next-IFD field exists
- next IFD does not point into the header
- external values remain within TIFF data
- field counts stay within configured limits
- value byte sizes remain bounded

Guarded traversal additionally protects against cycles and excessive
traversal depth.


## 18. Relevant implementation

    photometa/parsers/tiff.py
    photometa/extractors/ifd0.py
    photometa/extractors/exif_ifd.py
    photometa/extractors/gps_ifd.py
    photometa/parsers/tags.py


## 19. Related documentation

    docs/tiff-structure.md
    docs/exif.md
    docs/exif-tags.md
    docs/parser-security.md
