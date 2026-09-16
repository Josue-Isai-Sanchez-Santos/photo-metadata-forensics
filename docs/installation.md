# Installation

## Requirements

PhotoMeta requires:

    Python >= 3.11

The base project dependencies are:

    Pillow >= 11.0
    defusedxml >= 0.7.1

## Development installation

From the repository root:

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e .

On Windows PowerShell, activate the virtual environment with the
corresponding PowerShell activation script.

## HEIC / HEIF support

Install the optional HEIF dependency:

    python -m pip install -e ".[heif]"

This installs:

    pillow-heif

## RAW support

Install the optional RAW dependency:

    python -m pip install -e ".[raw]"

This installs:

    rawpy

which uses LibRaw.

## All Python optional image backends

    python -m pip install -e ".[heif,raw]"

## ExifTool

ExifTool is external to the Python package.

It must be installed separately and available as:

    exiftool

in the system PATH.

It is only required when explicitly selecting:

    photometa scan FILE --backend exiftool

## Verify installation

    photometa --version

    photometa --help

## Development quality tools

The CI pipeline currently uses:

    ruff
    bandit
    pip-audit

They can be installed with:

    python -m pip install ruff bandit pip-audit
