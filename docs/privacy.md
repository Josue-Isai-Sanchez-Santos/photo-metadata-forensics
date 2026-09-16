# Privacy Analysis

## Purpose

PhotoMeta identifies metadata fields that may expose personal, location or
device information.

A privacy finding means the metadata is present.

It does not mean the image is malicious.

## Metadata sources

Privacy analysis can inspect supported fields from:

    IFD0
    ExifIFD
    GPS IFD
    XMP
    IPTC

## Examples of findings

Findings can include:

- GPS coordinates
- GPS altitude
- original capture date
- camera/device model
- camera or lens serial identifiers
- owner/creator information
- software information
- copyright/author information
- unique identifiers
- location fields

## Severity

Findings use:

    low
    medium
    high

Severity is a project classification for metadata exposure.

It is not a probability of harm.

## Exposure score

Score version:

    1.0

Current documented matrix:

| Finding | Points |
| --- | ---: |
| GPS coordinates | 40 |
| Device/lens serial number | 20 |
| Original capture date | 10 |
| Device model | 10 |
| Owner/creator information | 10 |
| Software information | 5 |
| Copyright/author information | 5 |

Total:

    100

Score levels:

    LOW       below 25
    MEDIUM    25 through 49
    HIGH      50 or higher

The 0-100 value represents points in this documented matrix.

It is explicitly not a probability of:

- compromise
- stalking
- tracking
- identification
- harm
- forensic certainty

## Commands

    photometa privacy image.jpg

    photometa privacy image.jpg --detailed

    photometa privacy directory/ --recursive

## Exact location handling

Exact coordinates are intentionally hidden in some exported/reporting modes
unless the user explicitly enables sensitive output.
