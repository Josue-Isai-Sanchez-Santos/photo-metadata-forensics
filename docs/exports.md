# Export and Reporting Formats

## JSON

Native JPEG single-file scan:

    photometa scan image.jpg --json

Current JSON schema version:

    1.0

Exact GPS data is omitted unless explicitly enabled:

    photometa scan image.jpg --json --include-sensitive

Directory scans can also be serialized to JSON.

Single-file JSON for RAW, HEIC/HEIF and the additional Pillow formats is
currently not implemented.

## CSV

CSV is a directory/batch export:

    photometa scan images/ --csv result.csv

CSV cannot be combined with:

    --json
    --segments
    --include-sensitive

The output file can be excluded from the same scan to avoid scanning the
file being generated.

## HTML

Comprehensive report:

    photometa report image.jpg

Default:

    report.html

Custom:

    photometa report image.jpg -o result.html

HTML output is standalone.

Existing output is not replaced unless:

    --force

Exact GPS coordinates remain hidden unless:

    --include-sensitive

## Text report

    photometa report image.jpg --text

This preserves the earlier terminal-oriented report format.

## Privacy principle

Machine-readable and human-readable outputs deliberately avoid exposing
exact coordinates by default where the option is supported.
