import tempfile
import unittest
from pathlib import Path

from photometa.parsers.icc import (
    ICC_IDENTIFIER,
    IccParserError,
    extract_icc_profile_from_jpeg,
    is_icc_segment,
    parse_icc_chunk,
    parse_icc_profile,
    reassemble_icc_chunks,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)


def create_desc_payload(
    name: str,
) -> bytes:

    encoded = (
        name.encode(
            "ascii"
        )
        + b"\x00"
    )

    return (
        b"desc"
        + b"\x00" * 4
        + len(encoded).to_bytes(
            4,
            "big",
        )
        + encoded
    )


def create_mluc_payload(
    name: str,
) -> bytes:

    encoded = name.encode(
        "utf-16-be"
    )

    record_offset = (
        16
        + 12
    )

    return (
        b"mluc"
        + b"\x00" * 4
        + (1).to_bytes(
            4,
            "big",
        )
        + (12).to_bytes(
            4,
            "big",
        )
        + b"en"
        + b"US"
        + len(encoded).to_bytes(
            4,
            "big",
        )
        + record_offset.to_bytes(
            4,
            "big",
        )
        + encoded
    )


def create_icc_profile(
    name: str = "Test RGB Profile",
    profile_class: bytes = b"mntr",
    color_space: bytes = b"RGB ",
    description_type: str = "desc",
) -> bytes:

    if description_type == "desc":

        description = (
            create_desc_payload(
                name
            )
        )

    elif description_type == "mluc":

        description = (
            create_mluc_payload(
                name
            )
        )

    else:
        raise ValueError(
            description_type
        )

    tag_count = 1

    tag_table_size = (
        4
        + tag_count * 12
    )

    description_offset = (
        128
        + tag_table_size
    )

    profile_size = (
        description_offset
        + len(description)
    )

    header = bytearray(
        128
    )

    header[0:4] = (
        profile_size.to_bytes(
            4,
            "big",
        )
    )

    # Preferred CMM.
    header[4:8] = b"TEST"

    # ICC version 4.3.0.
    header[8] = 4
    header[9] = 0x30

    header[12:16] = (
        profile_class
    )

    header[16:20] = (
        color_space
    )

    # Profile Connection Space.
    header[20:24] = b"XYZ "

    # Required ICC signature.
    header[36:40] = b"acsp"

    # Platform.
    header[40:44] = b"APPL"

    # Device manufacturer / model.
    header[48:52] = b"TEST"
    header[52:56] = b"MODL"

    # Profile creator.
    header[80:84] = b"TEST"

    tag_table = bytearray()

    tag_table += (
        tag_count.to_bytes(
            4,
            "big",
        )
    )

    tag_table += b"desc"

    tag_table += (
        description_offset.to_bytes(
            4,
            "big",
        )
    )

    tag_table += (
        len(description).to_bytes(
            4,
            "big",
        )
    )

    return bytes(
        header
        + tag_table
        + description
    )


def create_icc_segment(
    data: bytes,
    sequence: int = 1,
    total: int = 1,
) -> JpegSegment:

    payload = (
        ICC_IDENTIFIER
        + bytes(
            (
                sequence,
                total,
            )
        )
        + data
    )

    return JpegSegment(
        offset=2,
        marker=0xE2,
        name="APP2",
        declared_length=(
            len(payload) + 2
        ),
        payload_length=len(payload),
        is_exif=False,
        payload=payload,
    )


def create_jpeg_with_icc(
    profile: bytes,
    chunks: int = 1,
) -> bytes:

    if chunks <= 0:
        raise ValueError(
            chunks
        )

    chunk_size = (
        len(profile)
        + chunks
        - 1
    ) // chunks

    output = bytearray(
        b"\xFF\xD8"
    )

    for index in range(
        chunks
    ):

        start = (
            index
            * chunk_size
        )

        end = min(
            start
            + chunk_size,
            len(profile),
        )

        data = profile[
            start:end
        ]

        payload = (
            ICC_IDENTIFIER
            + bytes(
                (
                    index + 1,
                    chunks,
                )
            )
            + data
        )

        length = (
            len(payload)
            + 2
        )

        output += b"\xFF\xE2"

        output += length.to_bytes(
            2,
            "big",
        )

        output += payload

    output += (
        b"\xFF\xDA"
        b"\x00\x02"
    )

    return bytes(output)


class TestIccParser(
    unittest.TestCase
):

    def test_detects_icc_app2(
        self,
    ):

        profile = create_icc_profile()

        segment = create_icc_segment(
            profile
        )

        self.assertTrue(
            is_icc_segment(
                segment
            )
        )

    def test_parses_icc_chunk(
        self,
    ):

        profile = create_icc_profile()

        chunk = parse_icc_chunk(
            create_icc_segment(
                profile,
                sequence=1,
                total=2,
            )
        )

        self.assertEqual(
            chunk.sequence_number,
            1,
        )

        self.assertEqual(
            chunk.total_chunks,
            2,
        )

        self.assertEqual(
            chunk.data,
            profile,
        )

    def test_parses_header_and_description(
        self,
    ):

        profile = parse_icc_profile(
            create_icc_profile()
        )

        self.assertEqual(
            profile.profile_name,
            "Test RGB Profile",
        )

        self.assertEqual(
            profile.color_space,
            "RGB",
        )

        self.assertEqual(
            profile.profile_class,
            "Display device",
        )

        self.assertEqual(
            profile.version,
            "4.3.0",
        )

        self.assertEqual(
            profile.header.pcs,
            "CIE XYZ",
        )

    def test_parses_mluc_description(
        self,
    ):

        profile = parse_icc_profile(
            create_icc_profile(
                name="Modern ICC Profile",
                description_type="mluc",
            )
        )

        self.assertEqual(
            profile.profile_name,
            "Modern ICC Profile",
        )

    def test_reassembles_multiple_chunks(
        self,
    ):

        profile = create_icc_profile()

        middle = (
            len(profile)
            // 2
        )

        first = parse_icc_chunk(
            create_icc_segment(
                profile[:middle],
                sequence=1,
                total=2,
            )
        )

        second = parse_icc_chunk(
            create_icc_segment(
                profile[middle:],
                sequence=2,
                total=2,
            )
        )

        rebuilt = reassemble_icc_chunks(
            (
                second,
                first,
            )
        )

        self.assertEqual(
            rebuilt,
            profile,
        )

    def test_extracts_multichunk_icc_from_jpeg(
        self,
    ):

        profile_data = (
            create_icc_profile()
        )

        jpeg = create_jpeg_with_icc(
            profile_data,
            chunks=2,
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "icc.jpg"
            )

            path.write_bytes(
                jpeg
            )

            profile = (
                extract_icc_profile_from_jpeg(
                    path
                )
            )

        self.assertIsNotNone(
            profile
        )

        assert profile is not None

        self.assertEqual(
            profile.profile_name,
            "Test RGB Profile",
        )

        self.assertEqual(
            profile.chunk_count,
            2,
        )

    def test_returns_none_without_icc(
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
                / "no-icc.jpg"
            )

            path.write_bytes(
                jpeg
            )

            profile = (
                extract_icc_profile_from_jpeg(
                    path
                )
            )

        self.assertIsNone(
            profile
        )

    def test_rejects_missing_chunk(
        self,
    ):

        profile = create_icc_profile()

        first = parse_icc_chunk(
            create_icc_segment(
                profile,
                sequence=1,
                total=2,
            )
        )

        with self.assertRaises(
            IccParserError
        ):
            reassemble_icc_chunks(
                (first,)
            )

    def test_rejects_invalid_icc_signature(
        self,
    ):

        profile = bytearray(
            create_icc_profile()
        )

        profile[36:40] = b"FAIL"

        with self.assertRaises(
            IccParserError
        ):
            parse_icc_profile(
                bytes(profile)
            )


if __name__ == "__main__":
    unittest.main()
