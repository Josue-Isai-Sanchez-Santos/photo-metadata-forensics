import tempfile
import unittest
from pathlib import Path

from photometa.extractors.ifd0 import (
    Ifd0ExtractorError,
    extract_ifd0_from_jpeg,
    extract_ifd0_metadata,
)
from photometa.parsers.exif import (
    parse_exif,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)


def _uint16(
    value: int,
) -> bytes:
    return value.to_bytes(
        2,
        "little",
    )


def _uint32(
    value: int,
) -> bytes:
    return value.to_bytes(
        4,
        "little",
    )


def _rational(
    numerator: int,
    denominator: int,
) -> bytes:
    return (
        _uint32(numerator)
        + _uint32(denominator)
    )


def create_tiff_data() -> bytes:
    """
    Construye un TIFF little-endian con:

    ImageDescription = Sample photo
    Make             = Samsung
    Model            = SM-S938B
    Orientation      = 1
    XResolution      = 72/1
    YResolution      = 72/1
    ResolutionUnit   = 2
    Software         = One UI Camera
    DateTime         = 2026:08:11 14:32:51
    Copyright        = Test Copyright
    """

    fields = [
        (
            0x010E,
            2,
            b"Sample photo\x00",
        ),
        (
            0x010F,
            2,
            b"Samsung\x00",
        ),
        (
            0x0110,
            2,
            b"SM-S938B\x00",
        ),
        (
            0x0112,
            3,
            _uint16(1),
        ),
        (
            0x011A,
            5,
            _rational(72, 1),
        ),
        (
            0x011B,
            5,
            _rational(72, 1),
        ),
        (
            0x0128,
            3,
            _uint16(2),
        ),
        (
            0x0131,
            2,
            b"One UI Camera\x00",
        ),
        (
            0x0132,
            2,
            b"2026:08:11 14:32:51\x00",
        ),
        (
            0x8298,
            2,
            b"Test Copyright\x00",
        ),
    ]

    entry_count = len(fields)

    ifd0_offset = 8

    external_data_offset = (
        ifd0_offset
        + 2
        + (entry_count * 12)
        + 4
    )

    entries = bytearray()
    external = bytearray()

    for tag, field_type, raw in fields:

        if field_type == 2:
            count = len(raw)

        elif field_type == 3:
            count = len(raw) // 2

        elif field_type == 5:
            count = len(raw) // 8

        else:
            raise ValueError(
                "Tipo no esperado en muestra."
            )

        entries += _uint16(tag)
        entries += _uint16(field_type)
        entries += _uint32(count)

        if len(raw) <= 4:
            entries += raw.ljust(
                4,
                b"\x00",
            )

        else:
            value_offset = (
                external_data_offset
                + len(external)
            )

            entries += _uint32(
                value_offset
            )

            external += raw

    tiff = bytearray()

    # TIFF header.
    tiff += b"II"
    tiff += b"\x2A\x00"
    tiff += _uint32(
        ifd0_offset
    )

    # IFD0.
    tiff += _uint16(
        entry_count
    )

    tiff += entries

    # No hay siguiente IFD.
    tiff += b"\x00\x00\x00\x00"

    # Valores que no cabían inline.
    tiff += external

    return bytes(tiff)


def create_exif_segment() -> JpegSegment:

    payload = (
        b"Exif\x00\x00"
        + create_tiff_data()
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


def create_jpeg_bytes() -> bytes:

    payload = (
        b"Exif\x00\x00"
        + create_tiff_data()
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


class TestIfd0Extractor(unittest.TestCase):

    def test_extracts_all_initial_ifd0_tags(
        self,
    ):

        metadata = extract_ifd0_metadata(
            parse_exif(
                create_exif_segment()
            )
        )

        self.assertEqual(
            metadata.get(
                "ImageDescription"
            ),
            "Sample photo",
        )

        self.assertEqual(
            metadata.get("Make"),
            "Samsung",
        )

        self.assertEqual(
            metadata.get("Model"),
            "SM-S938B",
        )

        self.assertEqual(
            metadata.get("Orientation"),
            1,
        )

        self.assertEqual(
            str(
                metadata.get(
                    "XResolution"
                )
            ),
            "72",
        )

        self.assertEqual(
            str(
                metadata.get(
                    "YResolution"
                )
            ),
            "72",
        )

        self.assertEqual(
            metadata.get(
                "ResolutionUnit"
            ),
            2,
        )

        self.assertEqual(
            metadata.get("Software"),
            "One UI Camera",
        )

        self.assertEqual(
            metadata.get("DateTime"),
            "2026:08:11 14:32:51",
        )

        self.assertEqual(
            metadata.get("Copyright"),
            "Test Copyright",
        )

    def test_keeps_low_level_information(
        self,
    ):

        metadata = extract_ifd0_metadata(
            parse_exif(
                create_exif_segment()
            )
        )

        make = next(
            entry
            for entry in metadata.entries
            if entry.tag_name == "Make"
        )

        self.assertEqual(
            make.tag,
            0x010F,
        )

        self.assertEqual(
            make.tag_hex,
            "0x010F",
        )

        self.assertEqual(
            make.field_type_name,
            "ASCII",
        )

        self.assertEqual(
            make.value,
            "Samsung",
        )

    def test_converts_to_dict(
        self,
    ):

        metadata = extract_ifd0_metadata(
            parse_exif(
                create_exif_segment()
            )
        )

        result = metadata.as_dict()

        self.assertEqual(
            result["Make"],
            "Samsung",
        )

        self.assertEqual(
            result["Model"],
            "SM-S938B",
        )

    def test_extracts_from_jpeg_file(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.jpg"
            )

            path.write_bytes(
                create_jpeg_bytes()
            )

            metadata = (
                extract_ifd0_from_jpeg(
                    path
                )
            )

        self.assertEqual(
            metadata.get("Make"),
            "Samsung",
        )

        self.assertEqual(
            metadata.get("Model"),
            "SM-S938B",
        )

    def test_rejects_jpeg_without_exif(
        self,
    ):

        jpeg = (
            b"\xFF\xD8"
            b"\xFF\xDA"
            b"\x00\x02"
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "without-exif.jpg"
            )

            path.write_bytes(
                jpeg
            )

            with self.assertRaises(
                Ifd0ExtractorError
            ):
                extract_ifd0_from_jpeg(
                    path
                )


if __name__ == "__main__":
    unittest.main()
