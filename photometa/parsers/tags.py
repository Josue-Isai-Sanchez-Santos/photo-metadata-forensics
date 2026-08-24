from __future__ import annotations


TIFF_TAG_NAMES: dict[int, str] = {
    0x0100: "ImageWidth",
    0x0101: "ImageLength",
    0x0102: "BitsPerSample",
    0x0103: "Compression",
    0x0106: "PhotometricInterpretation",
    0x010E: "ImageDescription",
    0x010F: "Make",
    0x0110: "Model",
    0x0111: "StripOffsets",
    0x0112: "Orientation",
    0x0115: "SamplesPerPixel",
    0x0116: "RowsPerStrip",
    0x0117: "StripByteCounts",
    0x011A: "XResolution",
    0x011B: "YResolution",
    0x011C: "PlanarConfiguration",
    0x0128: "ResolutionUnit",
    0x0131: "Software",
    0x0132: "DateTime",
    0x013B: "Artist",
    0x013E: "WhitePoint",
    0x013F: "PrimaryChromaticities",
    0x0211: "YCbCrCoefficients",
    0x0212: "YCbCrSubSampling",
    0x0213: "YCbCrPositioning",
    0x0214: "ReferenceBlackWhite",
    0x8298: "Copyright",

    # Punteros.
    0x8769: "ExifIFDPointer",
    0x8825: "GPSInfoIFDPointer",
}


EXIF_IFD_TAG_NAMES: dict[int, str] = {
    # Exposición.
    0x829A: "ExposureTime",
    0x829D: "FNumber",
    0x8822: "ExposureProgram",

    # Sensibilidad.
    0x8827: "PhotographicSensitivity",
    0x8830: "SensitivityType",
    0x8831: "StandardOutputSensitivity",
    0x8832: "RecommendedExposureIndex",
    0x8833: "ISOSpeed",
    0x8834: "ISOSpeedLatitudeyyy",
    0x8835: "ISOSpeedLatitudezzz",

    # Versiones y fechas.
    0x9000: "ExifVersion",
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",

    # Configuración y condiciones de captura.
    0x9101: "ComponentsConfiguration",
    0x9102: "CompressedBitsPerPixel",

    0x9201: "ShutterSpeedValue",
    0x9202: "ApertureValue",
    0x9203: "BrightnessValue",
    0x9204: "ExposureBiasValue",
    0x9205: "MaxApertureValue",
    0x9206: "SubjectDistance",
    0x9207: "MeteringMode",
    0x9208: "LightSource",
    0x9209: "Flash",
    0x920A: "FocalLength",

    # Otros datos habituales.
    0x927C: "MakerNote",
    0x9286: "UserComment",

    # Color y dimensiones.
    0xA001: "ColorSpace",
    0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",

    # Condiciones de captura ampliadas.
    0xA401: "CustomRendered",
    0xA402: "ExposureMode",
    0xA403: "WhiteBalance",
    0xA404: "DigitalZoomRatio",
    0xA405: "FocalLengthIn35mmFilm",
    0xA406: "SceneCaptureType",
    0xA407: "GainControl",
    0xA408: "Contrast",
    0xA409: "Saturation",
    0xA40A: "Sharpness",

    # Lente.
    0xA432: "LensSpecification",
    0xA433: "LensMake",
    0xA434: "LensModel",
    0xA435: "LensSerialNumber",
}


def get_tiff_tag_name(
    tag: int,
) -> str:
    return TIFF_TAG_NAMES.get(
        tag,
        f"UnknownTag_{tag:04X}",
    )


def get_exif_tag_name(
    tag: int,
) -> str:
    return EXIF_IFD_TAG_NAMES.get(
        tag,
        f"UnknownExifTag_{tag:04X}",
    )
