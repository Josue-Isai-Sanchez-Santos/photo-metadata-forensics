# PhotoMeta Documentation

PhotoMeta is an educational metadata, privacy and forensic-analysis toolkit
for image files.

This documentation describes the implementation that exists in this
repository. It does not attempt to replace the JPEG, TIFF, EXIF, XMP, ICC
or IPTC specifications.

## Getting started

- [Installation](installation.md)
- [Command-line interface](cli.md)
- [Supported formats](supported-formats.md)
- [Project architecture](architecture.md)

## Binary structures and metadata

- [JPEG structure](jpeg-structure.md)
- [TIFF structure](tiff-structure.md)
- [Image File Directories](ifd.md)
- [EXIF](exif.md)
- [Supported EXIF/TIFF/GPS tags](exif-tags.md)
- [XMP, ICC and IPTC](metadata-formats.md)

## Analysis

- [Privacy analysis](privacy.md)
- [JPEG sanitization](sanitization.md)
- [Image comparison](comparison.md)
- [Anomaly analysis](anomalies.md)

## Output and interoperability

- [JSON, CSV and HTML exports](exports.md)
- [Optional and external backends](external-backends.md)

## Development and safety

- [Parser security and resource limits](parser-security.md)
- [Testing and continuous integration](testing-ci.md)
- [Current limitations and interpretation rules](limitations.md)

## Core principle

Metadata and structural differences are evidence to inspect.

They are not, by themselves, proof that an image is authentic, manipulated,
malicious, original or unmodified.
