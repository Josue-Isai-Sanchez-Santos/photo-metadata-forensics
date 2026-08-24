from __future__ import annotations


ORIENTATION_VALUES: dict[int, str] = {
    1: "Horizontal (normal)",
    2: "Mirror horizontal",
    3: "Rotate 180°",
    4: "Mirror vertical",
    5: "Mirror horizontal and rotate 270° CW",
    6: "Rotate 90° CW",
    7: "Mirror horizontal and rotate 90° CW",
    8: "Rotate 270° CW",
}


EXPOSURE_PROGRAM_VALUES: dict[int, str] = {
    0: "Not defined",
    1: "Manual",
    2: "Program AE",
    3: "Aperture-priority AE",
    4: "Shutter speed priority AE",
    5: "Creative (slow speed)",
    6: "Action (high speed)",
    7: "Portrait",
    8: "Landscape",
}


METERING_MODE_VALUES: dict[int, str] = {
    0: "Unknown",
    1: "Average",
    2: "Center-weighted average",
    3: "Spot",
    4: "Multi-spot",
    5: "Multi-segment",
    6: "Partial",
    255: "Other",
}


WHITE_BALANCE_VALUES: dict[int, str] = {
    0: "Auto",
    1: "Manual",
}


SCENE_CAPTURE_TYPE_VALUES: dict[int, str] = {
    0: "Standard",
    1: "Landscape",
    2: "Portrait",
    3: "Night",
    # Observado en algunos dispositivos,
    # pero no forma parte del conjunto
    # estándar clásico de valores EXIF.
    4: "Other (non-standard)",
}


COLOR_SPACE_VALUES: dict[int, str] = {
    0x0001: "sRGB",

    # Valores no estándar pero observados
    # por herramientas ampliamente usadas.
    0x0002: "Adobe RGB (non-standard)",
    0xFFFD: "Wide Gamut RGB (non-standard)",
    0xFFFE: "ICC Profile (non-standard)",

    0xFFFF: "Uncalibrated",
}


FLASH_VALUES: dict[int, str] = {
    0x00: "No Flash",
    0x01: "Fired",
    0x05: "Fired, return not detected",
    0x07: "Fired, return detected",

    0x08: "On, did not fire",
    0x09: "On, fired",
    0x0D: "On, return not detected",
    0x0F: "On, return detected",

    0x10: "Off, did not fire",
    0x14: "Off, did not fire, return not detected",

    0x18: "Auto, did not fire",
    0x19: "Auto, fired",
    0x1D: "Auto, fired, return not detected",
    0x1F: "Auto, fired, return detected",

    0x20: "No flash function",
    0x30: "Off, no flash function",

    0x41: "Fired, red-eye reduction",
    0x45: "Fired, red-eye reduction, return not detected",
    0x47: "Fired, red-eye reduction, return detected",

    0x49: "On, red-eye reduction",
    0x4D: "On, red-eye reduction, return not detected",
    0x4F: "On, red-eye reduction, return detected",

    0x50: "Off, red-eye reduction",

    0x58: "Auto, did not fire, red-eye reduction",
    0x59: "Auto, fired, red-eye reduction",
    0x5D: "Auto, fired, red-eye reduction, return not detected",
    0x5F: "Auto, fired, red-eye reduction, return detected",
}


#
# Semántica de Exif 3.x.
#
# En Exif 2.32 y anteriores, 0/1 se describían
# históricamente respecto al nivel del mar.
# Exif 3.x corrigió 0/1 para el elipsoide
# y añadió 2/3 para referencia de nivel del mar.
#
GPS_ALTITUDE_REF_VALUES: dict[int, str] = {
    0: "Positive ellipsoidal height",
    1: "Negative ellipsoidal height",
    2: "Positive sea-level altitude",
    3: "Negative sea-level altitude",
}


def _interpret_integer(
    value: object,
    mapping: dict[int, str],
    field_name: str,
) -> str:

    if not isinstance(value, int):
        return (
            f"Invalid {field_name} value: "
            f"{value!r}"
        )

    return mapping.get(
        value,
        f"Unknown ({value})",
    )


def interpret_orientation(
    value: object,
) -> str:

    return _interpret_integer(
        value,
        ORIENTATION_VALUES,
        "Orientation",
    )


def interpret_exposure_program(
    value: object,
) -> str:

    return _interpret_integer(
        value,
        EXPOSURE_PROGRAM_VALUES,
        "ExposureProgram",
    )


def interpret_metering_mode(
    value: object,
) -> str:

    return _interpret_integer(
        value,
        METERING_MODE_VALUES,
        "MeteringMode",
    )


def interpret_white_balance(
    value: object,
) -> str:

    return _interpret_integer(
        value,
        WHITE_BALANCE_VALUES,
        "WhiteBalance",
    )


def interpret_scene_capture_type(
    value: object,
) -> str:

    return _interpret_integer(
        value,
        SCENE_CAPTURE_TYPE_VALUES,
        "SceneCaptureType",
    )


def interpret_color_space(
    value: object,
) -> str:

    return _interpret_integer(
        value,
        COLOR_SPACE_VALUES,
        "ColorSpace",
    )


def interpret_flash(
    value: object,
) -> str:

    if not isinstance(value, int):
        return (
            f"Invalid Flash value: "
            f"{value!r}"
        )

    return FLASH_VALUES.get(
        value,
        f"Unknown flash value (0x{value:X})",
    )


def interpret_gps_altitude_ref(
    value: object,
) -> str:

    return _interpret_integer(
        value,
        GPS_ALTITUDE_REF_VALUES,
        "GPSAltitudeRef",
    )


SPECIAL_FIELD_INTERPRETERS = {
    "Orientation": interpret_orientation,
    "ExposureProgram": interpret_exposure_program,
    "MeteringMode": interpret_metering_mode,
    "Flash": interpret_flash,
    "WhiteBalance": interpret_white_balance,
    "SceneCaptureType": interpret_scene_capture_type,
    "ColorSpace": interpret_color_space,
    "GPSAltitudeRef": interpret_gps_altitude_ref,
}


def interpret_special_field(
    name: str,
    value: object,
) -> str:
    """
    Interpreta un campo especial conocido.

    El valor original nunca se modifica.
    """

    interpreter = (
        SPECIAL_FIELD_INTERPRETERS.get(
            name
        )
    )

    if interpreter is None:
        return str(value)

    return interpreter(
        value
    )
