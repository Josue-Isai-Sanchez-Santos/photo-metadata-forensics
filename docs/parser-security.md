# Parser Security and Resource Limits

PhotoMeta treats image files and metadata as untrusted input.

The native parser never assumes that offsets, counts, lengths, pointers or
metadata structures are well formed.

The limits described here are defensive operational limits chosen by
PhotoMeta. They are not claims about the theoretical maximum values allowed
by JPEG, TIFF, EXIF, XMP, ICC or IPTC standards.

## Threat model

The native parser is designed to reject malformed or excessively complex
input before it can cause unbounded traversal or resource consumption.

Examples include:

    offsets outside the available data
    truncated JPEG segments
    excessive JPEG segment counts
    excessive marker fill bytes
    oversized cumulative metadata
    absurd TIFF component counts
    oversized TIFF values
    repeated or circular IFD pointers
    excessive IFD depth
    excessive IFD node counts
    oversized XMP packets
    DTD or ENTITY declarations in XMP
    excessive XML node counts
    excessive XMP property counts
    excessive ICC chunks
    oversized reconstructed ICC profiles
    excessive ICC tag counts
    excessive Photoshop Image Resources
    excessive IPTC DataSets
    oversized IPTC values
    excessive IPTC extended-length descriptors

## Default native parser limits

Whole input:

    Maximum native JPEG input size:
        1 GiB

JPEG:

    Maximum segments:
        4096

    Maximum FF marker-fill bytes:
        1024

    Maximum payload in one JPEG segment:
        65533 bytes

    Maximum cumulative JPEG header payload:
        32 MiB

TIFF / EXIF:

    Maximum entries in one IFD:
        4096

    Maximum components in one TIFF value:
        65536

    Maximum decoded TIFF value size:
        16 MiB

    Maximum guarded IFD depth:
        16

    Maximum guarded IFD nodes:
        64

XMP:

    Maximum XMP packet size:
        2 MiB

    Maximum XML nodes:
        20000

    Maximum extracted properties:
        10000

    DTD and ENTITY declarations:
        rejected

ICC:

    Maximum reconstructed profile size:
        32 MiB

    Maximum ICC chunks:
        255

    Maximum ICC tags:
        4096

Photoshop / IPTC:

    Maximum Photoshop resources:
        4096

    Maximum Photoshop APP13 payload:
        16 MiB

    Maximum individual Photoshop resource:
        8 MiB

    Maximum IPTC data size:
        16 MiB

    Maximum IPTC DataSets:
        10000

    Maximum individual IPTC value:
        8 MiB

    Maximum extended-length descriptor:
        8 octets

## TIFF traversal

PhotoMeta tracks visited IFD offsets while following the IFD relationships
that its native EXIF implementation supports.

A repeated offset is rejected as a circular or repeated pointer.

Traversal also has independent depth and total-node budgets.

This prevents structures such as:

    A -> A

    A -> B -> A

    A -> B -> C -> ... without bound

PhotoMeta does not claim to implement arbitrary traversal of every possible
TIFF SubIFD structure.

## Range arithmetic

Python integers do not wrap like fixed-width C integers.

Nevertheless, attacker-controlled counts can still create huge ranges,
loops or allocations.

PhotoMeta therefore validates counts and available byte ranges before
allocating or iterating over attacker-controlled structures.

## XML

XMP packets are size-limited before XML parsing.

DTD and ENTITY declarations are rejected because PhotoMeta does not require
them for its supported XMP functionality.

XML node and extracted-property budgets provide additional complexity
limits.

The packet-size limit remains an important first-line bound because XML
parsers may allocate structures while parsing.

## Batch behavior

A malformed JPEG is a failure of that individual file, not of the complete
directory scan.

Batch processing records the per-file error and continues with subsequent
files.

## Security corpus

A small local corpus can be generated with:

    python tools/generate_security_corpus.py

It is written under:

    samples/private/security-corpus/

That directory is intentionally ignored by Git.

The corpus contains small reproducible malformed or hostile test inputs.
Very large files are not stored merely to test size limits; unit tests use
configurable low limits instead.

## Scope

These limits primarily protect PhotoMeta's native JPEG, TIFF/EXIF, XMP, ICC
and IPTC parsing paths.

Optional external backends such as Pillow, libheif, LibRaw and ExifTool have
their own implementations and resource behavior.

PhotoMeta's parser hardening is not a sandbox, antivirus product, malware
scanner or formal proof that every possible malformed input is harmless.

Parser rejection also says nothing about whether an image is authentic,
manipulated or malicious in intent.

The goal is deterministic failure and bounded native parsing when presented
with malformed or excessively complex metadata.
