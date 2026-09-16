# Current Limitations and Interpretation Rules

## Scope

PhotoMeta is an educational and forensic-analysis toolkit, not a universal
image decoder or authenticity-verification system.

## JPEG

The native header parser stops after the first SOS.

Complete JPEG traversal used by comparison/sanitization is implemented by a
separate rewriter.

## TIFF / EXIF

PhotoMeta implements the TIFF and EXIF structures required by its current
metadata features.

It does not claim arbitrary support for every TIFF extension, SubIFD graph,
EXIF revision or manufacturer MakerNote format.

## Extended XMP

Extended XMP is recognized, but the project does not claim complete support
for every possible extended-packet reconstruction case.

## Additional formats

PNG, WebP and standalone TIFF currently use a basic Pillow inspection path.

HEIC/HEIF and RAW use optional external backends.

Their feature depth is not equivalent to native JPEG support.

## ExifTool

ExifTool is optional.

It is a compatibility/reference backend, not a truth oracle.

Differences between ExifTool and PhotoMeta require investigation.

## Privacy score

The score is a documented rule-based exposure matrix.

It is not a probability of harm or compromise.

## Anomalies

An anomaly is not proof of manipulation.

Absence of anomalies is not proof of authenticity.

## Comparison

Recompression assessments are heuristic.

Different file hashes do not by themselves prove re-encoding.

Equal compressed-scan hashes provide useful evidence but are not a formal
proof of identical decoded pixels under all circumstances.

## Metadata provenance

Metadata can be created, copied, edited or removed.

Therefore metadata alone cannot establish provenance with certainty.

## Parser security

Defensive resource limits reduce risk from malformed inputs.

They do not turn PhotoMeta into a sandbox, antivirus engine or proof that
arbitrary hostile files are harmless.
