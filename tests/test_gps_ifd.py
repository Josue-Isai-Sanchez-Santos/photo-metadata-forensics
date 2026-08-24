import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from photometa.extractors.gps_ifd import (
    GpsIfdExtractorError,
    build_location_summary,
    dms_to_decimal,
    extract_gps_ifd_from_jpeg,
    extract_gps_ifd_metadata,
)
from photometa.parsers.exif import (
    parse_exif,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)


TYPE_SIZES = {
    1: 1,
    2: 1,
    3: 2,
    4: 4,
    5: 8,
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
        u32(numerator)
        + u32(denominator)
    )


def build_gps_tiff() -> bytes:

    latitude = (
        rational(19, 1)
        + rational(25, 1)
        + rational(35868, 625)
    )

    longitude = (
        rational(99, 1)
        + rational(7, 1)
        + rational(148881, 2500)
    )

    gps_time = (
        rational(16, 1)
        + rational(32, 1)
        + rational(51, 1)
    )

    fields = [
        (
            0x0001,
            2,
            b"N\x00",
        ),
        (
            0x0002,
            5,
            latitude,
        ),
        (
            0x0003,
            2,
            b"W\x00",
        ),
        (
            0x0004,
            5,
            longitude,
        ),
        (
            0x0005,
            1,
            b"\x00",
        ),
        (
            0x0006,
            5,
            rational(2240, 1),
        ),
        (
            0x0007,
            5,
            gps_time,
        ),
        (
            0x0010,
            2,
            b"T\x00",
        ),
        (
            0x0011,
            5,
            rational(12345, 100),
        ),
        (
            0x001D,
            2,
            b"2026:08:11\x00",
        ),
    ]

    ifd0_offset = 8

    #
    # IFD0:
    # count = 1
    # GPSInfoIFDPointer = 12 bytes
    # next IFD = 4 bytes
    #
    gps_ifd_offset = (
        ifd0_offset
        + 2
        + 12
        + 4
    )

    gps_external_offset = (
        gps_ifd_offset
        + 2
        + (len(fields) * 12)
        + 4
    )

    gps_entries = bytearray()
    external = bytearray()

    for tag, field_type, raw in fields:

        component_size = (
            TYPE_SIZES[field_type]
        )

        count = (
            len(raw)
            // component_size
        )

        gps_entries += u16(tag)
        gps_entries += u16(
            field_type
        )
        gps_entries += u32(count)

        if len(raw) <= 4:

            gps_entries += raw.ljust(
                4,
                b"\x00",
            )

        else:

            value_offset = (
                gps_external_offset
                + len(external)
            )

            gps_entries += u32(
                value_offset
            )

            external += raw

    tiff = bytearray()

    # TIFF header.
    tiff += b"II"
    tiff += b"\x2A\x00"
    tiff += u32(
        ifd0_offset
    )

    # IFD0.
    tiff += u16(1)

    # GPSInfoIFDPointer.
    tiff += u16(
        0x8825
    )
    tiff += u16(
        4
    )
    tiff += u32(
        1
    )
    tiff += u32(
        gps_ifd_offset
    )

    # Next IFD.
    tiff += u32(0)

    # GPS IFD.
    tiff += u16(
        len(fields)
    )

    tiff += gps_entries

    # Next GPS IFD.
    tiff += u32(0)

    # Datos externos.
    tiff += external

    return bytes(tiff)


def create_exif_segment() -> JpegSegment:

    payload = (
        b"Exif\x00\x00"
        + build_gps_tiff()
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
        + build_gps_tiff()
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


class TestGpsIfdExtractor(
    unittest.TestCase
):

    def test_extracts_gps_ifd(
        self,
    ):

        metadata = (
            extract_gps_ifd_metadata(
                parse_exif(
                    create_exif_segment()
                )
            )
        )

        self.assertEqual(
            metadata.get(
                "GPSLatitudeRef"
            ),
            "N",
        )

        self.assertEqual(
            metadata.get(
                "GPSLatitude"
            ),
            (
                Fraction(19, 1),
                Fraction(25, 1),
                Fraction(35868, 625),
            ),
        )

        self.assertEqual(
            metadata.get(
                "GPSLongitudeRef"
            ),
            "W",
        )

        self.assertEqual(
            metadata.get(
                "GPSAltitude"
            ),
            Fraction(2240, 1),
        )

        self.assertEqual(
            metadata.get(
                "GPSDateStamp"
            ),
            "2026:08:11",
        )

        self.assertEqual(
            metadata.get(
                "GPSImgDirection"
            ),
            Fraction(2469, 20),
        )

    def test_converts_dms_to_decimal(
        self,
    ):

        latitude = dms_to_decimal(
            (
                Fraction(19, 1),
                Fraction(25, 1),
                Fraction(35868, 625),
            ),
            "N",
        )

        longitude = dms_to_decimal(
            (
                Fraction(99, 1),
                Fraction(7, 1),
                Fraction(
                    148881,
                    2500,
                ),
            ),
            "W",
        )

        self.assertAlmostEqual(
            latitude,
            19.432608,
            places=6,
        )

        self.assertAlmostEqual(
            longitude,
            -99.133209,
            places=6,
        )

    def test_builds_location_summary(
        self,
    ):

        metadata = (
            extract_gps_ifd_metadata(
                parse_exif(
                    create_exif_segment()
                )
            )
        )

        summary = build_location_summary(
            metadata
        )

        self.assertTrue(
            summary.gps_detected
        )

        self.assertAlmostEqual(
            summary.latitude,
            19.432608,
            places=6,
        )

        self.assertAlmostEqual(
            summary.longitude,
            -99.133209,
            places=6,
        )

        self.assertEqual(
            summary.altitude,
            2240.0,
        )

        self.assertEqual(
            summary.gps_date,
            "2026-08-11",
        )

        self.assertEqual(
            summary.gps_time,
            "16:32:51 UTC",
        )

        self.assertAlmostEqual(
            summary.image_direction,
            123.45,
            places=2,
        )

    def test_extracts_from_jpeg(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "gps.jpg"
            )

            path.write_bytes(
                create_jpeg()
            )

            metadata = (
                extract_gps_ifd_from_jpeg(
                    path
                )
            )

        self.assertEqual(
            metadata.get(
                "GPSLatitudeRef"
            ),
            "N",
        )

        self.assertEqual(
            metadata.get(
                "GPSLongitudeRef"
            ),
            "W",
        )

    def test_rejects_missing_gps_pointer(
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
            GpsIfdExtractorError
        ):
            extract_gps_ifd_metadata(
                exif
            )

    def test_rejects_invalid_reference(
        self,
    ):

        with self.assertRaises(
            GpsIfdExtractorError
        ):
            dms_to_decimal(
                (
                    Fraction(19, 1),
                    Fraction(25, 1),
                    Fraction(0, 1),
                ),
                "X",
            )


if __name__ == "__main__":
    unittest.main()
