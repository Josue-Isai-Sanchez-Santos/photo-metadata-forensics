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


class TestIfdParser(unittest.TestCase):

    def test_parses_ifd_entry(self):

        data = (
            b"II"
            b"\x2A\x00"
            b"\x08\x00\x00\x00"

            b"\x01\x00"

            b"\x0F\x01"
            b"\x02\x00"
            b"\x08\x00\x00\x00"
            b"\x1A\x00\x00\x00"

            b"\x00\x00\x00\x00"

            b"Samsung\x00"
        )

        from photometa.parsers.tiff import (
            parse_ifd,
            parse_tiff_header,
        )

        header = parse_tiff_header(data)

        ifd = parse_ifd(
            data,
            header.first_ifd_offset,
            header.byte_order,
        )

        self.assertEqual(
            ifd.offset,
            8,
        )

        self.assertEqual(
            len(ifd.entries),
            1,
        )

        entry = ifd.entries[0]

        self.assertEqual(
            entry.tag,
            0x010F,
        )

        self.assertEqual(
            entry.tag_hex,
            "0x010F",
        )

        self.assertEqual(
            entry.field_type,
            2,
        )

        self.assertEqual(
            entry.count,
            8,
        )

        self.assertEqual(
            entry.value_or_offset,
            b"\x1A\x00\x00\x00",
        )

        self.assertEqual(
            ifd.next_ifd_offset,
            0,
        )

    def test_rejects_truncated_ifd(self):

        data = (
            b"II"
            b"\x2A\x00"
            b"\x08\x00\x00\x00"

            b"\x02\x00"

            b"\x0F\x01"
        )

        from photometa.parsers.tiff import (
            TiffParserError,
            parse_ifd,
            parse_tiff_header,
        )

        header = parse_tiff_header(data)

        with self.assertRaises(
            TiffParserError
        ):
            parse_ifd(
                data,
                header.first_ifd_offset,
                header.byte_order,
            )
