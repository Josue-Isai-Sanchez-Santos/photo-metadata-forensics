# Photo Metadata Forensics

PhotoMeta is an educational image-metadata, privacy and forensic-analysis
toolkit written in Python.

The project combines a native JPEG/TIFF/EXIF parser with optional mature
backends for broader image-format compatibility.

Its purpose is to make low-level metadata structures visible while keeping
raw evidence, interpretation and forensic heuristics clearly separated.

## Features

PhotoMeta currently supports:

- native JPEG marker parsing
- TIFF and EXIF parsing
- IFD0, ExifIFD and GPS IFD extraction
- little-endian and big-endian TIFF
- XMP metadata
- ICC profiles
- Photoshop APP13 / IPTC metadata
- GPS conversion and presentation
- privacy-sensitive metadata analysis
- rule-based privacy exposure score
- metadata/JPEG anomaly analysis
- JPEG-to-JPEG forensic comparison
- DQT and DHT fingerprints
- compressed JPEG scan-data hashing
- SHA-256, SHA-1 and MD5 file hashes
- full and selective JPEG metadata sanitization
- directory/batch analysis
- JSON export
- CSV batch export
- standalone HTML reports
- basic PNG, WebP and TIFF inspection
- optional HEIC/HEIF support
- optional RAW support through LibRaw
- optional ExifTool compatibility backend
- defensive parser resource limits
- automated CI on Python 3.11 and 3.14

## Installation

PhotoMeta requires Python 3.11 or newer.

### Quick install with pipx

For users who only want to use PhotoMeta, `pipx` is the recommended
installation method because it keeps PhotoMeta isolated while making the
`photometa` command available from any directory.

With `pipx` already installed:

    pipx install git+https://github.com/Josue-Isai-Sanchez-Santos/photo-metadata-forensics.git

Verify the installation:

    photometa --version

    photometa --help

After this installation, PhotoMeta can be used directly:

    photometa scan photo.jpg

    photometa privacy photo.jpg

    photometa gps photo.jpg

### Standard installation from source

Clone the repository:

    git clone https://github.com/Josue-Isai-Sanchez-Santos/photo-metadata-forensics.git

    cd photo-metadata-forensics

Create a virtual environment:

    python3 -m venv .venv

Linux, macOS or WSL:

    source .venv/bin/activate

Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

Install PhotoMeta:

    python -m pip install --upgrade pip

    python -m pip install .

Then:

    photometa --help

When using this installation method, activate the virtual environment again
whenever a new terminal is opened.

### Development installation

Contributors who want changes in the source tree to become immediately
available should use an editable installation:

    python -m pip install -e .

Optional development installation with all supported Python image backends:

    python -m pip install -e ".[heif,raw]"

### Optional image backends

HEIC / HEIF:

    python -m pip install ".[heif]"

RAW:

    python -m pip install ".[raw]"

Both:

    python -m pip install ".[heif,raw]"

ExifTool is an optional external executable and must be installed separately
when using:

    photometa scan FILE --backend exiftool

For complete installation instructions, see:

[Installation documentation](docs/installation.md)

## CLI

General help:

    photometa --help

Scan:

    photometa scan image.jpg

JPEG structure:

    photometa scan image.jpg --segments

Privacy:

    photometa privacy image.jpg

GPS:

    photometa gps image.jpg

HTML report:

    photometa report image.jpg

Hash:

    photometa hash image.jpg

Anomalies:

    photometa anomalies image.jpg

Compare two JPEG files:

    photometa compare original.jpg copy.jpg

Sanitized copy:

    photometa scrub image.jpg

Selective GPS scrub:

    photometa scrub image.jpg --gps

Privacy-oriented scrub:

    photometa scrub image.jpg --privacy

Batch scan:

    photometa scan images/ --recursive

JSON:

    photometa scan image.jpg --json

CSV:

    photometa scan images/ --csv result.csv

ExifTool backend:

    photometa scan image.jpg --backend exiftool

## Supported formats

| Format | Support |
| --- | --- |
| JPEG | Full native metadata/forensic path |
| PNG | Basic Pillow inspection |
| WebP | Basic Pillow inspection |
| TIFF | Basic standalone inspection; native TIFF parser used inside JPEG EXIF |
| HEIC/HEIF | Optional `pillow-heif` backend |
| RAW | Optional `rawpy` / LibRaw backend |

## Documentation

Start here:

[Documentation index](docs/index.md)

Technical documentation includes:

- [JPEG structure](docs/jpeg-structure.md)
- [TIFF structure](docs/tiff-structure.md)
- [Image File Directories](docs/ifd.md)
- [EXIF](docs/exif.md)
- [EXIF/TIFF/GPS tags](docs/exif-tags.md)
- [XMP, ICC and IPTC](docs/metadata-formats.md)
- [Privacy analysis](docs/privacy.md)
- [Sanitization](docs/sanitization.md)
- [Comparison](docs/comparison.md)
- [Anomalies](docs/anomalies.md)
- [Supported formats](docs/supported-formats.md)
- [Optional backends](docs/external-backends.md)
- [Exports](docs/exports.md)
- [Parser security](docs/parser-security.md)
- [Testing and CI](docs/testing-ci.md)
- [Limitations](docs/limitations.md)

## Project architecture

    photometa/
    ├── analysis/
    ├── backends/
    ├── exporters/
    ├── extractors/
    ├── formats/
    ├── interpretation/
    ├── parsers/
    ├── presentation/
    └── sanitization/

The native parser is intentionally retained as an educational implementation.

External tools such as ExifTool complement it instead of replacing it.

## Quality and security

The project includes:

- unit/regression tests
- malformed-metadata security tests
- defensive parser budgets
- Ruff linting
- Bandit static security analysis
- dependency auditing with pip-audit
- GitHub Actions CI

## Forensic interpretation

PhotoMeta deliberately avoids claims that metadata alone can prove image
authenticity or manipulation.

Important principles:

    metadata present != authentic

    metadata absent != manipulated

    anomaly != proof of manipulation

    no anomaly != proof of authenticity

    file hash mismatch != proof of recompression

Comparison and recompression results are investigative heuristics, not
provenance guarantees.

## License

See the repository license for the terms under which this project is
distributed.
