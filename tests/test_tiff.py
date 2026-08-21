import struct
import unittest
from fractions import Fraction

from photometa.parsers.tiff import (
    IfdEntry,
    TiffParserError,
    decode_ascii_value,
    decode_ifd_value,
    get_ifd_entry_data_size,
    get_ifd_entry_raw_value,
    parse_ifd,
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

        with self.assertRaises(
            TiffParserError
        ):
            parse_tiff_header(data)

    def test_rejects_invalid_magic_number(self):

        data = (
            b"II"
            b"\x29\x00"
            b"\x08\x00\x00\x00"
        )

        with self.assertRaises(
            TiffParserError
        ):
            parse_tiff_header(data)


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

        header = parse_tiff_header(
            data
        )

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
            entry.field_type_name,
            "ASCII",
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

        header = parse_tiff_header(
            data
        )

        with self.assertRaises(
            TiffParserError
        ):
            parse_ifd(
                data,
                header.first_ifd_offset,
                header.byte_order,
            )


class TestTiffRawValues(unittest.TestCase):

    def test_calculates_ascii_data_size(self):

        entry = IfdEntry(
            tag=0x010F,
            field_type=2,
            count=8,
            value_or_offset=(
                b"\x1A\x00\x00\x00"
            ),
        )

        self.assertEqual(
            get_ifd_entry_data_size(
                entry
            ),
            8,
        )

    def test_reads_offset_ascii_value(self):

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

        header = parse_tiff_header(
            data
        )

        ifd = parse_ifd(
            data,
            header.first_ifd_offset,
            header.byte_order,
        )

        raw = get_ifd_entry_raw_value(
            data,
            ifd.entries[0],
            header.byte_order,
        )

        self.assertEqual(
            raw,
            b"Samsung\x00",
        )

    def test_reads_inline_short_value(self):

        entry = IfdEntry(
            tag=0x0112,
            field_type=3,
            count=1,
            value_or_offset=(
                b"\x06\x00\x00\x00"
            ),
        )

        raw = get_ifd_entry_raw_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            raw,
            b"\x06\x00",
        )

    def test_decodes_ascii_value(self):

        self.assertEqual(
            decode_ascii_value(
                b"Samsung\x00"
            ),
            "Samsung",
        )


class TestTiffValueDecoder(unittest.TestCase):

    def test_decodes_byte(self):

        entry = IfdEntry(
            tag=0x0001,
            field_type=1,
            count=1,
            value_or_offset=(
                b"\x64\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            value,
            100,
        )

    def test_decodes_multiple_bytes(self):

        entry = IfdEntry(
            tag=0x0001,
            field_type=1,
            count=4,
            value_or_offset=(
                b"\x01\x02\x03\x04"
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            value,
            (1, 2, 3, 4),
        )

    def test_decodes_ascii(self):

        data = (
            b"\x00" * 8
            + b"Samsung\x00"
        )

        entry = IfdEntry(
            tag=0x010F,
            field_type=2,
            count=8,
            value_or_offset=(
                b"\x08\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            data,
            entry,
            "little",
        )

        self.assertEqual(
            value,
            "Samsung",
        )

    def test_decodes_short(self):

        entry = IfdEntry(
            tag=0x0112,
            field_type=3,
            count=1,
            value_or_offset=(
                b"\x06\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            value,
            6,
        )

    def test_decodes_big_endian_short(self):

        entry = IfdEntry(
            tag=0x0112,
            field_type=3,
            count=1,
            value_or_offset=(
                b"\x00\x06\x00\x00"
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "big",
        )

        self.assertEqual(
            value,
            6,
        )

    def test_decodes_long(self):

        entry = IfdEntry(
            tag=0x0100,
            field_type=4,
            count=1,
            value_or_offset=(
                (123456).to_bytes(
                    4,
                    "little",
                )
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            value,
            123456,
        )

    def test_decodes_rational(self):

        payload = (
            (1).to_bytes(
                4,
                "little",
            )
            +
            (125).to_bytes(
                4,
                "little",
            )
        )

        data = (
            b"\x00" * 8
            + payload
        )

        entry = IfdEntry(
            tag=0x829A,
            field_type=5,
            count=1,
            value_or_offset=(
                b"\x08\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            data,
            entry,
            "little",
        )

        self.assertEqual(
            value,
            Fraction(1, 125),
        )

    def test_rejects_zero_rational_denominator(self):

        payload = (
            (1).to_bytes(
                4,
                "little",
            )
            +
            (0).to_bytes(
                4,
                "little",
            )
        )

        data = (
            b"\x00" * 8
            + payload
        )

        entry = IfdEntry(
            tag=0x829A,
            field_type=5,
            count=1,
            value_or_offset=(
                b"\x08\x00\x00\x00"
            ),
        )

        with self.assertRaises(
            TiffParserError
        ):
            decode_ifd_value(
                data,
                entry,
                "little",
            )

    def test_decodes_sbyte(self):

        entry = IfdEntry(
            tag=0x0001,
            field_type=6,
            count=1,
            value_or_offset=(
                b"\xFE\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            value,
            -2,
        )

    def test_decodes_undefined(self):

        data = (
            b"\x00" * 8
            + b"ABCDEF"
        )

        entry = IfdEntry(
            tag=0x927C,
            field_type=7,
            count=6,
            value_or_offset=(
                b"\x08\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            data,
            entry,
            "little",
        )

        self.assertEqual(
            value,
            b"ABCDEF",
        )

    def test_decodes_sshort(self):

        value_bytes = (
            (-10).to_bytes(
                2,
                "little",
                signed=True,
            )
            + b"\x00\x00"
        )

        entry = IfdEntry(
            tag=0x0001,
            field_type=8,
            count=1,
            value_or_offset=value_bytes,
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            value,
            -10,
        )

    def test_decodes_slong(self):

        entry = IfdEntry(
            tag=0x0001,
            field_type=9,
            count=1,
            value_or_offset=(
                (-2).to_bytes(
                    4,
                    "little",
                    signed=True,
                )
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertEqual(
            value,
            -2,
        )

    def test_decodes_srational(self):

        payload = (
            (-1).to_bytes(
                4,
                "little",
                signed=True,
            )
            +
            (3).to_bytes(
                4,
                "little",
                signed=True,
            )
        )

        data = (
            b"\x00" * 8
            + payload
        )

        entry = IfdEntry(
            tag=0x9204,
            field_type=10,
            count=1,
            value_or_offset=(
                b"\x08\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            data,
            entry,
            "little",
        )

        self.assertEqual(
            value,
            Fraction(-1, 3),
        )

    def test_decodes_float(self):

        entry = IfdEntry(
            tag=0x0001,
            field_type=11,
            count=1,
            value_or_offset=(
                struct.pack(
                    "<f",
                    1.5,
                )
            ),
        )

        value = decode_ifd_value(
            b"",
            entry,
            "little",
        )

        self.assertAlmostEqual(
            value,
            1.5,
        )

    def test_decodes_double(self):

        payload = struct.pack(
            "<d",
            3.141592653589793,
        )

        data = (
            b"\x00" * 8
            + payload
        )

        entry = IfdEntry(
            tag=0x0001,
            field_type=12,
            count=1,
            value_or_offset=(
                b"\x08\x00\x00\x00"
            ),
        )

        value = decode_ifd_value(
            data,
            entry,
            "little",
        )

        self.assertAlmostEqual(
            value,
            3.141592653589793,
        )


if __name__ == "__main__":
    unittest.main()
