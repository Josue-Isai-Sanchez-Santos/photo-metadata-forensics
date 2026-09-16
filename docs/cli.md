# Command-Line Interface

## General form

    photometa COMMAND [OPTIONS]

Available commands:

    scan
    privacy
    gps
    report
    hash
    anomalies
    compare
    scrub

## Version

    photometa --version

## Scan

    photometa scan IMAGE

Performs a metadata and structure summary.

Native JPEG scans can additionally show header segments:

    photometa scan image.jpg --segments

Directory scan:

    photometa scan images/

Recursive directory scan:

    photometa scan images/ --recursive

JSON:

    photometa scan image.jpg --json

Exact GPS information is hidden from single-file JSON unless explicitly
requested:

    photometa scan image.jpg --json --include-sensitive

Directory CSV:

    photometa scan images/ --csv result.csv

External ExifTool backend:

    photometa scan image.jpg --backend exiftool

The ExifTool backend currently operates on one file at a time and does not
support PhotoMeta's native `--segments`, batch CSV or native JSON modes.

## Privacy

    photometa privacy image.jpg

Detailed findings and score contributions:

    photometa privacy image.jpg --detailed

Directory privacy analysis:

    photometa privacy images/

    photometa privacy images/ --recursive

## GPS

    photometa gps image.jpg

Include raw GPS IFD values:

    photometa gps image.jpg --raw

## Report

Default HTML report:

    photometa report image.jpg

Custom output:

    photometa report image.jpg -o report.html

Replace an existing output:

    photometa report image.jpg -o report.html --force

Include exact coordinates:

    photometa report image.jpg --include-sensitive

Legacy text report:

    photometa report image.jpg --text

## Hash

SHA-256 by default:

    photometa hash FILE

Other supported algorithms:

    photometa hash FILE --algorithm sha1
    photometa hash FILE --algorithm md5

Calculate all supported hashes:

    photometa hash FILE --all

Supported algorithms:

    SHA-256
    SHA-1
    MD5

Hash availability does not imply equal cryptographic suitability. SHA-256 is
the normal default.

## Anomalies

    photometa anomalies image.jpg

Reports supported structural, consistency and heuristic findings.

A finding is evidence worth reviewing, not proof of manipulation.

## Compare

    photometa compare original.jpg copy.jpg

Compares metadata presence and JPEG coding characteristics between two JPEG
files.

## Scrub

Full supported metadata scrub:

    photometa scrub image.jpg

Default output:

    image_clean.jpg

Custom output:

    photometa scrub image.jpg -o clean.jpg

GPS-only selective scrub:

    photometa scrub image.jpg --gps

Privacy-oriented selective scrub:

    photometa scrub image.jpg --privacy

Explicit full mode:

    photometa scrub image.jpg --all

The three scrub modes are mutually exclusive.

## Important option constraints

`--segments` is JPEG-specific.

Single-file JSON is currently implemented for the native JPEG scan path.

CSV export requires a directory.

`--include-sensitive` is intentionally explicit because exact coordinates
may expose sensitive location data.
