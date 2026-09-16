# JPEG Comparison

## Command

    photometa compare original.jpg copy.jpg

## Compared information

PhotoMeta records:

- whole-file SHA-256
- dimensions
- JPEG coding process
- EXIF presence
- GPS presence
- XMP presence
- IPTC presence
- ICC presence
- camera model when available
- quantization-table fingerprint
- Huffman-table fingerprint
- SHA-256 of compressed scan data

## Identical files

Equal whole-file SHA-256 means the compared files are byte-for-byte
identical.

## Metadata-only changes

Different whole-file hashes do not automatically imply recompression.

Metadata can change while the compressed JPEG scan data remains unchanged.

## Quantization tables

DQT payloads are fingerprinted.

Changes can provide evidence that JPEG coding characteristics differ.

## Huffman tables

DHT payloads are also fingerprinted.

## Scan data

PhotoMeta hashes the entropy-coded JPEG scan stream while traversing the
complete JPEG.

## Recompression assessment

Current levels include:

    NO EVIDENCE
    POSSIBLE
    LIKELY

These are heuristics.

`LIKELY` is not proof that a particular application recompressed or modified
an image.

## Interpretation rules

    whole-file hash mismatch
        != proof of recompression

    metadata difference
        != proof of pixel modification

    coding-table difference
        != proof of malicious editing

    no detected difference
        != proof of authenticity
