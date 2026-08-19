import unittest

from photometa.parsers.exif import (
    ExifParserError,
    parse_exif_tiff_header,
)
from photometa.parsers.jpeg import JpegSegment


class TestExifParser(unittest.TestCase):

    def test_extracts_tiff_header_from_exif(self):

        payload = (
            b"Exif\x00\x00"
            b"II"
            b"\x2A\x00"
            b"\x08\x00\x00\x00"
        )

        segment = JpegSegment(
            offset=2,
            marker=0xE1,
            name="APP1",
            declared_length=len(payload) + 2,
            payload_length=len(payload),
            is_exif=True,
            payload=payload,
        )

        header = parse_exif_tiff_header(
            segment
        )

        self.assertEqual(
            header.byte_order,
            "little",
        )

        self.assertEqual(
            header.magic_number,
            42,
        )

        self.assertEqual(
            header.first_ifd_offset,
            8,
        )

    def test_rejects_non_exif_app1(self):

        segment = JpegSegment(
            offset=2,
            marker=0xE1,
            name="APP1",
            declared_length=8,
            payload_length=6,
            is_exif=False,
            payload=b"ABCDEF",
        )

        with self.assertRaises(
            ExifParserError
        ):
            parse_exif_tiff_header(segment)


if __name__ == "__main__":
    unittest.main()
