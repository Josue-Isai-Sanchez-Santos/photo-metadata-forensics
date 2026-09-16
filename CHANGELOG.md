# Changelog

All notable changes to Photo Metadata Forensics will be documented in this file.

This project follows Semantic Versioning for its public releases.

## [1.0.0] - 2026-09-16

First public release of Photo Metadata Forensics (PhotoMeta).

### Added

- Command-line interface with eight commands:
  `scan`, `privacy`, `gps`, `report`, `hash`, `anomalies`, `compare` and `scrub`.
- Native JPEG structure and metadata inspection.
- TIFF, EXIF, IFD and GPS metadata parsing.
- XMP, ICC profile and Photoshop APP13/IPTC metadata inspection.
- Privacy-sensitive metadata detection and rule-based exposure scoring.
- File hashing with SHA-256, SHA-1 and MD5.
- JPEG anomaly analysis and forensic comparison.
- Full and selective JPEG metadata sanitization.
- Directory processing and recursive scanning.
- JSON and CSV export.
- Standalone HTML reports.
- Basic PNG, WebP and TIFF inspection.
- Optional HEIC/HEIF and RAW backends.
- Optional ExifTool compatibility backend.
- CLI branding and quick-start command examples.
- Installation, usage, architecture and technical documentation.
- MIT license.
- Automated tests and continuous integration.

### Packaging

- Established package version `1.0.0`.
- Added MIT license metadata to the Python package.
- Added the license file to source and wheel distributions.
- Documented installation with pipx, standard pip and editable mode.

### Important limitations

- Native forensic functionality focuses primarily on JPEG.
- Other image formats have different levels of feature support.
- Privacy scores are rule-based indicators, not probabilities of harm.
- Anomalies and metadata differences do not prove image manipulation.
- Metadata alone cannot establish image authenticity or provenance.
- Sanitization should be verified for the intended privacy requirements.

For details, see [the limitations documentation](docs/limitations.md).
