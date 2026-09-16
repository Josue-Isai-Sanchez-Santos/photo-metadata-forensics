# Testing and Continuous Integration

## Unit tests

Tests use Python's built-in:

    unittest

Run the complete suite with:

    python -m unittest discover -s tests -v

The repository includes coverage for:

- JPEG
- TIFF
- EXIF
- IFD extraction
- GPS
- XMP
- ICC
- IPTC
- privacy
- privacy score
- sanitization
- selective scrub
- comparison
- anomalies
- hashing
- batch analysis
- JSON
- CSV
- HTML
- PNG/WebP/TIFF
- HEIF
- RAW
- ExifTool backend
- parser-security regression cases
- CLI behavior

## Compilation check

    python -m compileall -q photometa tests tools

## Ruff

    ruff check photometa tests tools

The project targets Python 3.11 syntax compatibility for lint configuration.

## Bandit

    bandit -r photometa tools -ll

The current CI security gate checks Medium and High findings.

## Dependency audit

    pip-audit .

    python -m pip check

## GitHub Actions

Workflow:

    .github/workflows/ci.yml

Triggered by:

    push
    pull_request

Test matrix:

    Python 3.11
    Python 3.14

Quality/security job:

    Ruff
    Bandit
    pip-audit
    pip check

## Security corpus

Small malformed samples can be generated locally with:

    python tools/generate_security_corpus.py

They are stored below:

    samples/private/security-corpus/

and are intentionally excluded from Git.
