# Installation

## Overview

PhotoMeta can be installed in different ways depending on whether the goal
is to use the tool or modify its source code.

Recommended options:

    User:
        pipx

    User from source:
        virtual environment + pip install .

    Developer:
        virtual environment + pip install -e .


## Requirements

PhotoMeta requires:

    Python >= 3.11

Base Python dependencies:

    Pillow >= 11.0
    defusedxml >= 0.7.1

Git is also required when installing directly from the GitHub repository.


## 1. Quick install with pipx

This is the recommended method for a user who only wants to run PhotoMeta.

`pipx` installs Python command-line applications in isolated environments
while exposing their commands to the user.

Verify that pipx is available:

    pipx --version

Install PhotoMeta directly from GitHub:

    pipx install git+https://github.com/Josue-Isai-Sanchez-Santos/photo-metadata-forensics.git

Verify:

    photometa --version

    photometa --help

PhotoMeta can now be used from any directory:

    photometa scan photo.jpg

    photometa privacy photo.jpg

    photometa gps photo.jpg

There is no need to manually activate a PhotoMeta virtual environment when
using the pipx installation.


## 2. Standard installation from source

This method is useful when a user wants a local copy of the repository.

Clone the project:

    git clone https://github.com/Josue-Isai-Sanchez-Santos/photo-metadata-forensics.git

    cd photo-metadata-forensics


### Linux, macOS or WSL

Create a virtual environment:

    python3 -m venv .venv

Activate it:

    source .venv/bin/activate

Upgrade pip:

    python -m pip install --upgrade pip

Install PhotoMeta:

    python -m pip install .


### Windows PowerShell

Create a virtual environment:

    py -m venv .venv

Activate it:

    .\.venv\Scripts\Activate.ps1

Upgrade pip:

    python -m pip install --upgrade pip

Install PhotoMeta:

    python -m pip install .


## 3. Verify the source installation

After installation:

    photometa --version

    photometa --help

The command should display the PhotoMeta CLI:

    PHOTO METADATA FORENSICS

followed by the available commands.


## 4. Using PhotoMeta after a source installation

When PhotoMeta is installed inside a project virtual environment, that
environment must be activated again after opening a new terminal.

Linux, macOS or WSL:

    cd photo-metadata-forensics

    source .venv/bin/activate

Windows PowerShell:

    cd photo-metadata-forensics

    .\.venv\Scripts\Activate.ps1

Then PhotoMeta can be used normally:

    photometa scan photo.jpg

The image does not need to be stored inside the repository.

Absolute or relative paths can be used:

    photometa scan ~/Pictures/photo.jpg

    photometa scan ./images/photo.jpg


## 5. Development installation

Developers and contributors should use an editable installation.

Clone the repository and create a virtual environment as described above.

Then:

    python -m pip install -e .

Editable mode means changes made inside the local `photometa/` source tree
become available without reinstalling the package after every edit.

This mode is intended for development rather than normal end-user use.


## 6. HEIC / HEIF support

HEIC / HEIF support is optional.

From the repository root:

    python -m pip install ".[heif]"

This installs:

    pillow-heif


## 7. RAW support

RAW support is optional.

From the repository root:

    python -m pip install ".[raw]"

This installs:

    rawpy

which uses LibRaw.


## 8. Install all optional Python image backends

    python -m pip install ".[heif,raw]"

Developers can use editable mode:

    python -m pip install -e ".[heif,raw]"


## 9. ExifTool

ExifTool is not installed by PhotoMeta's Python package.

It is an optional external executable.

ExifTool only needs to be installed when explicitly using:

    photometa scan FILE --backend exiftool

The executable must be available in the system PATH as:

    exiftool

PhotoMeta's native backend remains the default.


## 10. First commands

Show help:

    photometa --help

Show version:

    photometa --version

Scan an image:

    photometa scan photo.jpg

Analyze privacy-sensitive metadata:

    photometa privacy photo.jpg

Extract GPS information:

    photometa gps photo.jpg

Generate an HTML report:

    photometa report photo.jpg --output report.html

Create a sanitized copy:

    photometa scrub photo.jpg --output photo_clean.jpg

Process a directory:

    photometa scan ./images/

Process subdirectories:

    photometa scan ./images/ --recursive


## 11. Leaving a virtual environment

For source or development installations:

    deactivate

This is not necessary for pipx installations because pipx manages the
isolated environment automatically.


## 12. Development quality tools

PhotoMeta's CI currently uses:

    ruff
    bandit
    pip-audit

Developers can install them with:

    python -m pip install ruff bandit pip-audit

Run Ruff:

    ruff check photometa tests tools

Run the complete test suite:

    python -m unittest discover -s tests -v

Run Bandit:

    bandit -r photometa tools -ll

Audit dependencies:

    pip-audit .

Check installed dependencies:

    python -m pip check


## Related documentation

Command-line reference:

    docs/cli.md

Supported image formats:

    docs/supported-formats.md

Optional and external backends:

    docs/external-backends.md

Documentation index:

    docs/index.md
