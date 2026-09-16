# Metadata and JPEG Anomaly Analysis

## Command

    photometa anomalies image.jpg

## Purpose

The anomaly analyzer looks for supported structural inconsistencies,
metadata conflicts and heuristic indicators worth reviewing.

## Categories

    structural
    consistency
    heuristic

## Severities

    low
    medium
    high

## Examples

Supported analysis includes cases such as:

- declared but corrupt EXIF
- duplicate tags
- suspicious/out-of-range structures
- multiple EXIF segments
- inconsistent dimensions
- malformed date fields
- conflicting date relationships
- incomplete Make/Model information
- GPS fields missing expected companion fields
- software strings associated with known editing tools

## Editing software

The presence of software such as Photoshop, Lightroom, GIMP, Snapseed or
another editor is not automatically evidence of image manipulation.

It is contextual metadata.

## Critical interpretation rule

An anomaly is evidence worth investigating.

It is not proof of:

- forgery
- editing
- malicious manipulation
- provenance

Likewise:

    no anomaly

does not mean:

    authentic
