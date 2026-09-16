# EXIF and TIFF Tags Supported by PhotoMeta

## 1. Purpose

This document lists the tag-name mappings currently implemented by
PhotoMeta.

It is intentionally implementation-focused.

It should not be interpreted as a complete list of every TIFF, EXIF or GPS
tag defined by their respective specifications.


## 2. Tag handling

PhotoMeta separates tag tables into:

    TIFF / IFD0 tags
    ExifIFD tags
    GPS IFD tags

When a numeric tag is not present in the current mapping, the parser does
not discard it.

It receives a generated name.


## 3. IFD0 / TIFF tag names

| Tag | Name |
| --- | --- |
| `0x0100` | ImageWidth |
| `0x0101` | ImageLength |
| `0x0102` | BitsPerSample |
| `0x0103` | Compression |
| `0x0106` | PhotometricInterpretation |
| `0x010E` | ImageDescription |
| `0x010F` | Make |
| `0x0110` | Model |
| `0x0111` | StripOffsets |
| `0x0112` | Orientation |
| `0x0115` | SamplesPerPixel |
| `0x0116` | RowsPerStrip |
| `0x0117` | StripByteCounts |
| `0x011A` | XResolution |
| `0x011B` | YResolution |
| `0x011C` | PlanarConfiguration |
| `0x0128` | ResolutionUnit |
| `0x0131` | Software |
| `0x0132` | DateTime |
| `0x013B` | Artist |
| `0x013E` | WhitePoint |
| `0x013F` | PrimaryChromaticities |
| `0x0211` | YCbCrCoefficients |
| `0x0212` | YCbCrSubSampling |
| `0x0213` | YCbCrPositioning |
| `0x0214` | ReferenceBlackWhite |
| `0x8298` | Copyright |
| `0x8769` | ExifIFDPointer |
| `0x8825` | GPSInfoIFDPointer |


## 4. ExifIFD tag names

### Exposure

| Tag | Name |
| --- | --- |
| `0x829A` | ExposureTime |
| `0x829D` | FNumber |
| `0x8822` | ExposureProgram |


### Sensitivity

| Tag | Name |
| --- | --- |
| `0x8827` | PhotographicSensitivity |
| `0x8830` | SensitivityType |
| `0x8831` | StandardOutputSensitivity |
| `0x8832` | RecommendedExposureIndex |
| `0x8833` | ISOSpeed |
| `0x8834` | ISOSpeedLatitudeyyy |
| `0x8835` | ISOSpeedLatitudezzz |


### Version and timestamps

| Tag | Name |
| --- | --- |
| `0x9000` | ExifVersion |
| `0x9003` | DateTimeOriginal |
| `0x9004` | DateTimeDigitized |


### Capture configuration

| Tag | Name |
| --- | --- |
| `0x9101` | ComponentsConfiguration |
| `0x9102` | CompressedBitsPerPixel |
| `0x9201` | ShutterSpeedValue |
| `0x9202` | ApertureValue |
| `0x9203` | BrightnessValue |
| `0x9204` | ExposureBiasValue |
| `0x9205` | MaxApertureValue |
| `0x9206` | SubjectDistance |
| `0x9207` | MeteringMode |
| `0x9208` | LightSource |
| `0x9209` | Flash |
| `0x920A` | FocalLength |


### Other EXIF fields

| Tag | Name |
| --- | --- |
| `0x927C` | MakerNote |
| `0x9286` | UserComment |


### Color and dimensions

| Tag | Name |
| --- | --- |
| `0xA001` | ColorSpace |
| `0xA002` | PixelXDimension |
| `0xA003` | PixelYDimension |


### Extended capture conditions

| Tag | Name |
| --- | --- |
| `0xA401` | CustomRendered |
| `0xA402` | ExposureMode |
| `0xA403` | WhiteBalance |
| `0xA404` | DigitalZoomRatio |
| `0xA405` | FocalLengthIn35mmFilm |
| `0xA406` | SceneCaptureType |
| `0xA407` | GainControl |
| `0xA408` | Contrast |
| `0xA409` | Saturation |
| `0xA40A` | Sharpness |
| `0xA420` | ImageUniqueID |
| `0xA430` | CameraOwnerName |
| `0xA431` | BodySerialNumber |


### Lens

| Tag | Name |
| --- | --- |
| `0xA432` | LensSpecification |
| `0xA433` | LensMake |
| `0xA434` | LensModel |
| `0xA435` | LensSerialNumber |


## 5. GPS IFD tag names

| Tag | Name |
| --- | --- |
| `0x0000` | GPSVersionID |
| `0x0001` | GPSLatitudeRef |
| `0x0002` | GPSLatitude |
| `0x0003` | GPSLongitudeRef |
| `0x0004` | GPSLongitude |
| `0x0005` | GPSAltitudeRef |
| `0x0006` | GPSAltitude |
| `0x0007` | GPSTimeStamp |
| `0x0008` | GPSSatellites |
| `0x0009` | GPSStatus |
| `0x000A` | GPSMeasureMode |
| `0x000B` | GPSDOP |
| `0x000C` | GPSSpeedRef |
| `0x000D` | GPSSpeed |
| `0x000E` | GPSTrackRef |
| `0x000F` | GPSTrack |
| `0x0010` | GPSImgDirectionRef |
| `0x0011` | GPSImgDirection |
| `0x0012` | GPSMapDatum |
| `0x001B` | GPSProcessingMethod |
| `0x001C` | GPSAreaInformation |
| `0x001D` | GPSDateStamp |
| `0x001E` | GPSDifferential |
| `0x001F` | GPSHPositioningError |


## 6. Unknown tags

PhotoMeta generates stable fallback names for tags not currently mapped.

IFD0 / TIFF:

    UnknownTag_XXXX

ExifIFD:

    UnknownExifTag_XXXX

GPS IFD:

    UnknownGpsTag_XXXX

The hexadecimal numeric tag is still available independently of the
friendly name.


## 7. Tags and values are separate concepts

A tag ID identifies the semantic field.

It does not by itself determine:

- the TIFF field type
- count
- storage location
- decoded value

Those properties come from the corresponding 12-byte IFD entry.

For example:

    0x0110 Model

may identify the meaning of the field, while the IFD entry still determines
how many ASCII bytes exist and where those bytes are stored.


## 8. Raw versus human interpretation

PhotoMeta keeps tag decoding and user-friendly interpretation separate.

Examples of higher-level interpretation include:

    Orientation
    ExposureProgram
    MeteringMode
    Flash
    ColorSpace
    WhiteBalance
    SceneCaptureType
    GPSAltitudeRef

The underlying numeric/raw value remains conceptually distinct from the
display label.


## 9. Privacy-sensitive examples

Some supported tags can expose sensitive or identifying information:

    GPSLatitude
    GPSLongitude
    GPSAltitude
    GPSDateStamp
    CameraOwnerName
    BodySerialNumber
    LensSerialNumber
    ImageUniqueID
    DateTimeOriginal

Whether a field is privacy-sensitive depends on its contents and context.

Presence of a tag does not prove malicious intent.


## 10. Forensic caution

EXIF tags are metadata fields, not authenticity guarantees.

They may be created, changed, removed or copied by software.

PhotoMeta therefore treats them as evidence to inspect rather than proof of
origin or manipulation.


## 11. Relevant implementation

    photometa/parsers/tags.py
    photometa/parsers/tiff.py
    photometa/extractors/ifd0.py
    photometa/extractors/exif_ifd.py
    photometa/extractors/gps_ifd.py


## 12. Related documentation

    docs/tiff-structure.md
    docs/ifd.md
    docs/exif.md
    docs/jpeg-structure.md
    docs/parser-security.md
