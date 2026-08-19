import unittest

from photometa.parsers.tiff import (
    TiffParserError,
    parse_tiff_header,
)


class TestTiffParser(unittest.TestCase):

    def test_parses_little_endian_header(self):

        data = (
            b"II"
            b"\x2A\x00"
            b"\x08\x00\x00\x00"
        )

        header = parse_tiff_header(data)

        self.assertEqual(
            header.byte_order_marker,
            b"II",
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

    def test_parses_big_endian_header(self):

        data = (
            b"MM"
            b"\x00\x2A"
            b"\x00\x00\x00\x08"
        )

        header = parse_tiff_header(data)

        self.assertEqual(
            header.byte_order_marker,
            b"MM",
        )

        self.assertEqual(
            header.byte_order,
            "big",
        )

        self.assertEqual(
            header.magic_number,
            42,
        )

        self.assertEqual(
            header.first_ifd_offset,
            8,
        )

    def test_rejects_invalid_byte_order(self):

        data = (
            b"XX"
            b"\x00\x2A"
            b"\x00\x00\x00\x08"
        )

        with self.assertRaises(TiffParserError):
            parse_tiff_header(data)

    def test_rejects_invalid_magic_number(self):

        data = (
            b"II"
            b"\x29\x00"
            b"\x08\x00\x00\x00"
        )

        with self.assertRaises(TiffParserError):
            parse_tiff_header(data)


if __name__ == "__main__":
    unittest.main()
