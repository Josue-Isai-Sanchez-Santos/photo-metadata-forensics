# Optional and External Backends

## Why backends exist

PhotoMeta's native parser is intentionally focused on understanding and
validating JPEG/TIFF/EXIF internals.

Mature external libraries expand format compatibility.

## Pillow

Base dependency.

Used for basic inspection of:

    PNG
    WebP
    TIFF

It can expose selected EXIF-like fields, XMP/ICC presence and image
properties.

## pillow-heif

Optional dependency:

    python -m pip install -e ".[heif]"

Used for HEIC/HEIF image inspection.

Container recognition is performed separately so unsupported/misclassified
ISO-BMFF formats such as AVIF are not automatically labeled HEIF.

## rawpy / LibRaw

Optional dependency:

    python -m pip install -e ".[raw]"

Used for RAW inspection.

PhotoMeta can report raw dimensions, visible dimensions, sensor/crop
information, white/black levels, white balance and selected capture/lens
fields exposed by LibRaw.

## ExifTool

External executable.

Selected with:

    photometa scan FILE --backend exiftool

PhotoMeta executes ExifTool with JSON/group output and applies a timeout.

ExifTool differences are useful compatibility/debugging evidence.

Agreement or disagreement between ExifTool and PhotoMeta does not prove
authenticity or manipulation.

## Backend boundaries

External backends have their own parsers, dependencies, limits and resource
behavior.

PhotoMeta's native parser security guarantees do not automatically apply to
third-party libraries.
