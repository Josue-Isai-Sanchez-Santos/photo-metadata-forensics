# JPEG Structure in PhotoMeta

## 1. Purpose

This document describes the JPEG structures that PhotoMeta currently
understands, inspects or preserves.

It is based on the implementation present in this repository and is
intended both as project documentation and as an educational reference.

PhotoMeta is not a complete JPEG decoder. Its native code focuses on:

- structural validation
- JPEG marker inspection
- metadata discovery
- forensic comparison
- privacy analysis
- metadata sanitization
- preservation of compressed image data

The native header parser deliberately stops at the first Start Of Scan
(`SOS`). A separate full-JPEG rewriter is used by operations that must
continue through entropy-coded scan data until End Of Image (`EOI`).


## 2. Simplified JPEG layout

A typical JPEG handled by PhotoMeta can be visualized as:

    SOI
     |
     +-- APP0        JFIF / JFXX
     |
     +-- APP1        EXIF
     |
     +-- APP1        XMP
     |
     +-- APP2        ICC profile
     |
     +-- APP13       Photoshop / IPTC
     |
     +-- DQT         Quantization tables
     |
     +-- SOF         Frame information
     |
     +-- DHT         Huffman tables
     |
     +-- DRI         Restart interval, if present
     |
     +-- SOS
     |
     +-- Entropy-coded image data
     |      |
     |      +-- FF00 byte stuffing
     |      +-- RST0-RST7 markers, when used
     |
     +-- EOI

This is an illustrative layout, not a requirement that every JPEG contain
all of these segments or that they always appear in this exact order.

Application segments can be absent, repeated or contain data not currently
interpreted by PhotoMeta.


## 3. JPEG marker representation

JPEG markers begin with byte:

    FF

followed by a marker code.

Examples:

    FF D8    SOI
    FF E0    APP0
    FF E1    APP1
    FF DB    DQT
    FF C0    SOF0
    FF C4    DHT
    FF DA    SOS
    FF D9    EOI

PhotoMeta stores the marker code separately and presents the complete value
using the `FFxx` notation.


## 4. Standalone markers

Some JPEG markers do not carry a length field.

PhotoMeta currently treats these as standalone markers:

    TEM
    SOI
    EOI
    RST0
    RST1
    RST2
    RST3
    RST4
    RST5
    RST6
    RST7

Their binary structure is essentially:

    FF
    marker

Other segments normally contain a two-byte length field.


## 5. Length-bearing JPEG segments

For a normal length-bearing segment PhotoMeta reads:

    FF
    marker
    length_hi
    length_lo
    payload...

The length is interpreted as a two-byte big-endian integer.

The declared JPEG length includes the two bytes occupied by the length
field itself.

Therefore PhotoMeta calculates:

    payload_length = declared_length - 2

A declared length smaller than 2 is rejected.

A segment whose declared payload extends beyond the available file data is
treated as truncated.


## 6. SOI — Start Of Image

Marker:

    FF D8

`SOI` marks the beginning of a JPEG image.

PhotoMeta requires the first two bytes of a JPEG processed by the native
parser to be:

    FF D8

If the file does not begin with that signature, it is rejected as not being
a valid JPEG for the native JPEG parser.

`SOI` is a standalone marker and does not have a length or payload.


## 7. APP0

Marker:

    FF E0

APP0 is an application-specific segment.

PhotoMeta does not assume that every APP0 contains the same kind of data.

During full metadata scrubbing, APP0 payloads beginning with:

    JFIF\0

or:

    JFXX\0

are preserved.

Other APP0 application data can be treated as removable metadata.

This distinction is important because JFIF/JFXX information can be part of
the technical representation of a JPEG rather than user-oriented metadata.


## 8. APP1

Marker:

    FF E1

APP1 is especially important to PhotoMeta because it can contain several
forms of metadata.


### 8.1 EXIF inside APP1

PhotoMeta identifies an EXIF APP1 segment when its payload begins with:

    Exif\0\0

After that six-byte identifier, PhotoMeta interprets the remaining bytes as
TIFF data.

Simplified structure:

    APP1
    |
    +-- Exif\0\0
        |
        +-- TIFF header
        |
        +-- IFD0
        |
        +-- ExifIFD
        |
        +-- GPS IFD

The TIFF parser supports both little-endian and big-endian byte order.

EXIF information extracted elsewhere in PhotoMeta includes fields such as:

- camera make and model
- timestamps
- exposure information
- focal length
- lens information
- camera owner fields
- serial identifiers
- GPS metadata

The presence or absence of EXIF metadata is not proof of image authenticity
or manipulation.


### 8.2 XMP inside APP1

PhotoMeta also recognizes standard XMP using the identifier:

    http://ns.adobe.com/xap/1.0/\0

It also recognizes the Extended XMP identifier:

    http://ns.adobe.com/xmp/extension/\0

The current project recognizes Extended XMP presence but does not claim
complete reconstruction of every possible Extended XMP packet layout.

XMP XML parsing is performed defensively.

PhotoMeta rejects DTD and ENTITY declarations and applies packet,
XML-node and extracted-property limits.

XMP can expose information including:

- creator information
- titles and descriptions
- software information
- location fields
- document identifiers
- EXIF/TIFF-derived XMP properties
- Google Camera properties

APP1 data that is neither recognized EXIF nor supported XMP is still
application metadata and can be removed by full sanitization.


## 9. APP2 — ICC profiles

Marker:

    FF E2

PhotoMeta identifies an ICC profile fragment when APP2 begins with:

    ICC_PROFILE\0

The JPEG ICC representation used by PhotoMeta contains:

    ICC_PROFILE\0
    sequence_number
    total_chunks
    profile_data

An ICC profile may span multiple APP2 segments.

PhotoMeta validates the sequence information and reconstructs the profile
from its chunks.

ICC profiles describe color-management information and are preserved by
the normal full metadata scrubber.

This is deliberate: ICC data affects color interpretation and is therefore
treated differently from ordinary descriptive metadata.


## 10. APP3 through APP12

Markers:

    FF E3
    ...
    FF EC

These are application-specific containers.

PhotoMeta's native project does not assign one universal semantic meaning
to these markers.

During full metadata sanitization they are treated as removable application
metadata.


## 11. APP13 — Photoshop and IPTC

Marker:

    FF ED

PhotoMeta recognizes Photoshop APP13 data when the payload starts with:

    Photoshop 3.0\0

Photoshop Image Resource Blocks inside the segment use the signature:

    8BIM

PhotoMeta searches those resources for IPTC data using resource ID:

    0x0404

The IPTC parser can extract fields such as:

- object name
- keywords
- date and time
- byline
- city
- sublocation
- province/state
- country
- headline
- credit
- source
- copyright notice
- caption
- writer/editor

PhotoMeta treats this metadata as potentially relevant to both forensic
inspection and privacy analysis.


## 12. APP14 — Adobe

Marker:

    FF EE

PhotoMeta preserves APP14 segments whose payload begins with:

    Adobe

because they may contain technical Adobe color-transform information.

APP14 data not recognized as the Adobe technical structure can be treated
as application metadata by the full scrubber.


## 13. APP15

Marker:

    FF EF

APP15 is treated as generic application metadata by PhotoMeta's current
sanitization logic.


## 14. COM — JPEG comments

Marker:

    FF FE

`COM` stores a JPEG comment.

PhotoMeta treats JPEG comments as metadata.

Full metadata sanitization can therefore remove them while preserving the
compressed image data.


## 15. DQT — Define Quantization Table

Marker:

    FF DB

`DQT` contains JPEG quantization-table data.

PhotoMeta does not use DQT merely as descriptive metadata. It is part of the
image coding structure.

During image comparison PhotoMeta collects DQT payloads and produces a
fingerprint from them.

A difference between quantization fingerprints is one possible indication
that JPEG coding data changed.

It is not, by itself, proof of recompression, editing or manipulation.


## 16. SOF — Start Of Frame

Start Of Frame segments contain information about the encoded image and the
JPEG coding process.

PhotoMeta's dimension extractor reads the beginning of the SOF payload as:

    sample precision    1 byte
    image height        2 bytes, big-endian
    image width         2 bytes, big-endian

Width and height must both be greater than zero.

PhotoMeta recognizes these SOF markers for JPEG dimensions and coding
process analysis:

| Marker | PhotoMeta process name |
| --- | --- |
| `FFC0` | Baseline DCT |
| `FFC1` | Extended sequential DCT |
| `FFC2` | Progressive DCT |
| `FFC3` | Lossless sequential |
| `FFC5` | Differential sequential DCT |
| `FFC6` | Differential progressive DCT |
| `FFC7` | Differential lossless |
| `FFC9` | Arithmetic sequential DCT |
| `FFCA` | Arithmetic progressive DCT |
| `FFCB` | Arithmetic lossless |
| `FFCD` | Differential arithmetic sequential |
| `FFCE` | Differential arithmetic progressive |
| `FFCF` | Differential arithmetic lossless |

The first supported SOF process found is used by the comparison snapshot to
describe the JPEG coding process.


## 17. DHT — Define Huffman Table

Marker:

    FF C4

`DHT` contains Huffman coding tables.

PhotoMeta records DHT payloads during complete JPEG inspection and
calculates a fingerprint over them.

If two compared JPEG files have different known DHT fingerprints,
PhotoMeta reports that their Huffman tables differ.

As with DQT, this is forensic comparison evidence, not proof of why the
difference occurred.


## 18. DAC — Define Arithmetic Coding Conditioning

Marker:

    FF CC

PhotoMeta recognizes the `DAC` marker name.

It belongs to JPEG arithmetic-coding structures.

The current project does not attempt to decode the image from DAC data.


## 19. DRI — Define Restart Interval

Marker:

    FF DD

PhotoMeta recognizes the `DRI` marker.

DRI is related to restart-marker intervals used within compressed JPEG scan
data.


## 20. RST0 through RST7

Markers:

    FF D0
    FF D1
    FF D2
    FF D3
    FF D4
    FF D5
    FF D6
    FF D7

Restart markers are standalone markers.

The complete JPEG rewriter recognizes and preserves restart markers while
traversing entropy-coded scan data.

They are not treated as metadata.


## 21. SOS — Start Of Scan

Marker:

    FF DA

`SOS` marks the beginning of entropy-coded scan data.

This marker is an important boundary inside PhotoMeta.

The native header iterator:

    photometa.parsers.jpeg.iter_jpeg_segments()

reads and yields the SOS segment and then stops.

This is intentional.

The header parser does not attempt to interpret entropy-coded image data.

Therefore:

    photometa scan image.jpg --segments

is a JPEG header/metadata-segment view rather than a complete dump of every
byte in the file.

The output itself explicitly states that the segment view stops at the
first SOS.


## 22. Entropy-coded scan data

After SOS, JPEG compressed image data begins.

PhotoMeta does not decode and re-encode this image data during metadata
sanitization.

The complete JPEG rewriter copies it while calculating a SHA-256 digest of
the scan data.

This allows the project to verify whether supported metadata sanitization
preserved the compressed JPEG image stream.


### 22.1 Byte stuffing

Within entropy-coded data, the sequence:

    FF 00

represents JPEG byte stuffing.

The complete rewriter understands this form while traversing scan data.

Outside compressed scan data, PhotoMeta's structural parser rejects `FF00`
as an invalid marker sequence.


### 22.2 Restart markers

`RST0` through `RST7` can appear inside scan data and are preserved by the
complete rewriter.


## 23. DNL — Define Number of Lines

Marker:

    FF DC

PhotoMeta recognizes `DNL`.

The complete JPEG rewriter specifically supports DNL appearing while a scan
is in progress and resumes scan processing afterwards.


## 24. EOI — End Of Image

Marker:

    FF D9

`EOI` marks the end of the JPEG image.

EOI is a standalone marker.

The native header iterator contains EOI support but normally stops at the
first SOS, so a normal header-segment listing does not continue far enough
to display EOI.

The complete JPEG rewriter, however, continues through the compressed scan
and requires an EOI marker to be present.

A complete JPEG processed by the rewriter without EOI is rejected.


## 25. Bytes after EOI

A file may contain bytes after its EOI marker.

The complete JPEG rewriter distinguishes the JPEG image from those trailing
bytes.

Depending on the operation, trailing bytes can either be preserved or
removed.

PhotoMeta's sanitization functionality can remove bytes after EOI without
decoding or re-encoding the JPEG image.


## 26. Other marker names recognized by PhotoMeta

The current native JPEG marker table also contains names for:

| Marker | Name |
| --- | --- |
| `FF01` | TEM |
| `FFC8` | JPG |
| `FFDE` | DHP |
| `FFDF` | EXP |

Unknown marker codes are not silently assigned a false meaning. The parser
represents them using a name based on their hexadecimal marker code.


## 27. Metadata containers used by PhotoMeta

The most important JPEG application segments for the current project are:

| Segment | Current PhotoMeta use |
| --- | --- |
| APP0 | JFIF/JFXX technical data |
| APP1 | EXIF |
| APP1 | XMP |
| APP2 | ICC profiles |
| APP13 | Photoshop Image Resources / IPTC |
| APP14 | Adobe technical color-transform data |
| COM | JPEG comments |

The application marker alone does not prove what the payload contains.

PhotoMeta checks payload identifiers before classifying EXIF, XMP, ICC or
Photoshop/IPTC data.


## 28. JPEG forensic comparison in PhotoMeta

PhotoMeta's comparison subsystem records several JPEG structural signals:

- image width and height
- JPEG coding process from SOF
- DQT payload fingerprint
- DHT payload fingerprint
- SHA-256 of entropy-coded scan data
- whole-file SHA-256
- EXIF presence
- GPS presence
- XMP presence
- ICC presence
- IPTC presence
- camera model when available

These signals can identify structural differences between two files.

They must not be interpreted as automatic proof of manipulation.

In particular:

- a different whole-file hash does not prove image recompression
- changed metadata alone does not prove pixel modification
- changed DQT/DHT or compressed scan data can support a recompression
  heuristic, but the conclusion remains heuristic
- unchanged supported structures do not prove authenticity


## 29. JPEG sanitization model

PhotoMeta's complete JPEG rewriter allows transformations only on:

    APP0 through APP15
    COM

Structural image-coding markers are not intended to be modified by the
metadata transformer.

The full scrub logic currently distinguishes between metadata that can be
removed and technical data that should normally remain.

Examples:

    preserve:
        JFIF / JFXX APP0
        ICC APP2
        Adobe APP14 technical data

    remove:
        EXIF APP1
        XMP APP1
        generic application metadata
        Photoshop / APP13 metadata
        JPEG COM comments

Selective scrub modes can apply more targeted changes instead of removing
all supported metadata.


## 30. Native parser security

JPEG files and their metadata are treated as untrusted input.

The JPEG parser therefore enforces defensive limits including:

- maximum input size
- maximum number of JPEG segments
- maximum marker-fill bytes
- maximum individual segment payload
- maximum cumulative header payload
- exact-length reads
- rejection of truncated structures

TIFF/EXIF, XMP, ICC, Photoshop and IPTC parsing have additional resource and
traversal limits.

See:

    docs/parser-security.md

for the complete security model and current default limits.


## 31. Current parser boundary

It is important to distinguish two JPEG paths in PhotoMeta.

### Header parser

    photometa/parsers/jpeg.py

Responsibilities:

- validate SOI
- enumerate header markers
- parse declared segment lengths
- enforce JPEG header security budgets
- identify EXIF APP1
- stop after the first SOS

### Complete JPEG rewriter

    photometa/sanitization/jpeg_rewriter.py

Responsibilities:

- traverse the complete JPEG
- preserve entropy-coded image data
- understand FF00 byte stuffing
- preserve restart markers
- support DNL interruptions
- reach and validate EOI
- optionally process metadata segments
- optionally remove bytes after EOI

Neither component is a general-purpose JPEG pixel decoder.


## 32. CLI inspection

JPEG header segments can be inspected with:

    photometa scan image.jpg --segments

The report includes:

    OFFSET
    MARKER
    TYPE
    LENGTH
    DETAIL

EXIF APP1 segments are explicitly identified in the detail column.


## 33. Relevant source files

This document reflects the implementation in the following project files:

    photometa/parsers/jpeg.py
    photometa/fileinfo.py
    photometa/parsers/exif.py
    photometa/parsers/xmp.py
    photometa/parsers/icc.py
    photometa/parsers/iptc.py
    photometa/analysis/comparison.py
    photometa/sanitization/jpeg_rewriter.py
    photometa/sanitization/scrub.py
    photometa/sanitization/selective.py
    photometa/presentation/scan.py

Related tests include:

    tests/test_jpeg.py
    tests/test_comparison.py
    tests/test_scrub.py
    tests/test_selective_scrub.py
    tests/test_parser_security.py
    tests/test_cli_commands.py

Related documentation:

    docs/parser-security.md


## 34. Scope and interpretation

This documentation describes what PhotoMeta currently implements.

It is not intended to replace the JPEG specification and does not claim that
PhotoMeta supports every JPEG extension, application payload or coding mode.

The project intentionally separates:

- low-level structural evidence
- metadata interpretation
- privacy analysis
- sanitization
- heuristic forensic comparison

A structural difference, metadata difference or parser warning must not be
treated by itself as proof that an image is authentic, manipulated or
malicious.
