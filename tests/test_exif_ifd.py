import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from photometa.extractors.exif_ifd import (
    ExifIfdExtractorError,
    build_capture_summary,
    extract_exif_ifd_from_jpeg,
    extract_exif_ifd_metadata,
)
from photometa.parsers.exif import (
    parse_exif,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)


TYPE_SIZES = {
    2: 1,
    3: 2,
    4: 4,
    5: 8,
    10: 8,
}


def u16(value: int) -> bytes:
    return value.to_bytes(
        2,
        "little",
    )


def u32(value: int) -> bytes:
    return value.to_bytes(
        4,
        "little",
    )


def rational(
    numerator: int,
    denominator: int,
) -> bytes:
    return (
        numerator.to_bytes(
            4,
            "little",
        )
        + denominator.to_bytes(
            4,
            "little",
        )
    )


def srational(
    numerator: int,
    denominator: int,
) -> bytes:
    return (
        numerator.to_bytes(
            4,
            "little",
            signed=True,
        )
        + denominator.to_bytes(
            4,
            "little",
            signed=True,
        )
    )


def build_exif_tiff() -> bytes:

    fields = [
        (
            0x829A,
            5,
            rational(1, 120),
        ),
        (
            0x829D,
            5,
            rational(17, 10),
        ),
        (
            0x8822,
            3,
            u16(2),
        ),
        (
            0x8827,
            3,
            u16(100),
        ),
        (
            0x9003,
            2,
            b"2026:08:11 14:32:51\x00",
        ),
        (
            0x9004,
            2,
            b"2026:08:11 14:32:51\x00",
        ),
        (
            0x9201,
            10,
            srational(689, 100),
        ),
        (
            0x9202,
            5,
            rational(153, 100),
        ),
        (
            0x9203,
            10,
            srational(2, 1),
        ),
        (
            0x9204,
            10,
            srational(-1, 3),
        ),
        (
            0x9205,
            5,
            rational(153, 100),
        ),
        (
            0x9207,
            3,
            u16(5),
        ),
        (
            0x9209,
            3,
            u16(0),
        ),
        (
            0x920A,
            5,
            rational(24, 1),
        ),
        (
            0xA001,
            3,
            u16(1),
        ),
        (
            0xA002,
            4,
            u32(4096),
        ),
        (
            0xA003,
            4,
            u32(3072),
        ),
        (
            0xA405,
            3,
            u16(24),
        ),
        (
            0xA433,
            2,
            b"nubia\x00",
        ),
        (
            0xA434,
            2,
            b"REDMAGIC Camera\x00",
        ),
    ]

    ifd0_offset = 8

    # IFD0:
    # 2 bytes count
    # 12 bytes ExifIFDPointer
    # 4 bytes next IFD
    exif_ifd_offset = (
        ifd0_offset
        + 2
        + 12
        + 4
    )

    exif_external_offset = (
        exif_ifd_offset
        + 2
        + (len(fields) * 12)
        + 4
    )

    exif_entries = bytearray()
    exif_external = bytearray()

    for tag, field_type, raw in fields:

        component_size = TYPE_SIZES[
            field_type
        ]

        count = (
            len(raw)
            // component_size
        )

        exif_entries += u16(tag)
        exif_entries += u16(
            field_type
        )
        exif_entries += u32(count)

        if len(raw) <= 4:

            exif_entries += raw.ljust(
                4,
                b"\x00",
            )

        else:

            value_offset = (
                exif_external_offset
                + len(exif_external)
            )

            exif_entries += u32(
                value_offset
            )

            exif_external += raw

    tiff = bytearray()

    # TIFF Header.
    tiff += b"II"
    tiff += b"\x2A\x00"
    tiff += u32(
        ifd0_offset
    )

    # IFD0 con ExifIFDPointer.
    tiff += u16(1)

    tiff += u16(
        0x8769
    )

    tiff += u16(
        4
    )

    tiff += u32(
        1
    )

    tiff += u32(
        exif_ifd_offset
    )

    # Next IFD.
    tiff += u32(0)

    # ExifIFD.
    tiff += u16(
        len(fields)
    )

    tiff += exif_entries

    # Next Exif IFD.
    tiff += u32(0)

    # Datos externos del ExifIFD.
    tiff += exif_external

    return bytes(tiff)


def create_exif_segment() -> JpegSegment:

    payload = (
        b"Exif\x00\x00"
        + build_exif_tiff()
    )

    return JpegSegment(
        offset=2,
        marker=0xE1,
        name="APP1",
        declared_length=(
            len(payload) + 2
        ),
        payload_length=len(payload),
        is_exif=True,
        payload=payload,
    )


def create_jpeg() -> bytes:

    payload = (
        b"Exif\x00\x00"
        + build_exif_tiff()
    )

    app1_length = (
        len(payload) + 2
    )

    return (
        b"\xFF\xD8"
        b"\xFF\xE1"
        + app1_length.to_bytes(
            2,
            "big",
        )
        + payload
        + b"\xFF\xDA"
        + b"\x00\x02"
    )


class TestExifIfdExtractor(
    unittest.TestCase
):

    def test_extracts_exif_ifd(
        self,
    ):

        metadata = (
            extract_exif_ifd_metadata(
                parse_exif(
                    create_exif_segment()
                )
            )
        )

        self.assertEqual(
            metadata.get(
                "ExposureTime"
            ),
            Fraction(1, 120),
        )

        self.assertEqual(
            metadata.get(
                "FNumber"
            ),
            Fraction(17, 10),
        )

        self.assertEqual(
            metadata.get(
                "ExposureProgram"
            ),
            2,
        )

        self.assertEqual(
            metadata.get_iso(),
            100,
        )

        self.assertEqual(
            metadata.get(
                "DateTimeOriginal"
            ),
            "2026:08:11 14:32:51",
        )

        self.assertEqual(
            metadata.get(
                "DateTimeDigitized"
            ),
            "2026:08:11 14:32:51",
        )

        self.assertEqual(
            metadata.get(
                "ShutterSpeedValue"
            ),
            Fraction(689, 100),
        )

        self.assertEqual(
            metadata.get(
                "ApertureValue"
            ),
            Fraction(153, 100),
        )

        self.assertEqual(
            metadata.get(
                "BrightnessValue"
            ),
            Fraction(2, 1),
        )

        self.assertEqual(
            metadata.get(
                "ExposureBiasValue"
            ),
            Fraction(-1, 3),
        )

        self.assertEqual(
            metadata.get(
                "MaxApertureValue"
            ),
            Fraction(153, 100),
        )

        self.assertEqual(
            metadata.get(
                "MeteringMode"
            ),
            5,
        )

        self.assertEqual(
            metadata.get("Flash"),
            0,
        )

        self.assertEqual(
            metadata.get(
                "FocalLength"
            ),
            Fraction(24, 1),
        )

        self.assertEqual(
            metadata.get(
                "ColorSpace"
            ),
            1,
        )

        self.assertEqual(
            metadata.get(
                "PixelXDimension"
            ),
            4096,
        )

        self.assertEqual(
            metadata.get(
                "PixelYDimension"
            ),
            3072,
        )

        self.assertEqual(
            metadata.get(
                "FocalLengthIn35mmFilm"
            ),
            24,
        )

        self.assertEqual(
            metadata.get(
                "LensMake"
            ),
            "nubia",
        )

        self.assertEqual(
            metadata.get(
                "LensModel"
            ),
            "REDMAGIC Camera",
        )

    def test_builds_capture_summary(
        self,
    ):

        metadata = (
            extract_exif_ifd_metadata(
                parse_exif(
                    create_exif_segment()
                )
            )
        )

        summary = build_capture_summary(
            metadata
        )

        self.assertEqual(
            summary.date,
            "2026-08-11",
        )

        self.assertEqual(
            summary.time,
            "14:32:51",
        )

        self.assertEqual(
            summary.exposure,
            "1/120 s",
        )

        self.assertEqual(
            summary.iso,
            100,
        )

        self.assertEqual(
            summary.aperture,
            "f/1.7",
        )

        self.assertEqual(
            summary.focal_length,
            "24 mm",
        )

        self.assertEqual(
            summary.lens,
            "nubia REDMAGIC Camera",
        )

    def test_extracts_from_jpeg(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.jpg"
            )

            path.write_bytes(
                create_jpeg()
            )

            metadata = (
                extract_exif_ifd_from_jpeg(
                    path
                )
            )

        self.assertEqual(
            metadata.get_iso(),
            100,
        )

        self.assertEqual(
            metadata.get(
                "FocalLength"
            ),
            Fraction(24, 1),
        )

    def test_rejects_missing_pointer(
        self,
    ):

        payload = (
            b"Exif\x00\x00"
            b"II"
            b"\x2A\x00"
            b"\x08\x00\x00\x00"
            b"\x00\x00"
            b"\x00\x00\x00\x00"
        )

        segment = JpegSegment(
            offset=2,
            marker=0xE1,
            name="APP1",
            declared_length=(
                len(payload) + 2
            ),
            payload_length=len(payload),
            is_exif=True,
            payload=payload,
        )

        exif = parse_exif(
            segment
        )

        with self.assertRaises(
            ExifIfdExtractorError
        ):
            extract_exif_ifd_metadata(
                exif
            )


if __name__ == "__main__":
    unittest.main()
