import tempfile
import unittest
from pathlib import Path

from photometa.parsers.iptc import (
    IPTC_RESOURCE_ID,
    IPTC_UTF8_DESIGNATOR,
    PHOTOSHOP_IDENTIFIER,
    IptcParserError,
    extract_iptc_from_jpeg,
    extract_iptc_resource,
    is_photoshop_app13,
    parse_iptc_iim,
    parse_photoshop_resources,
)
from photometa.parsers.jpeg import (
    JpegSegment,
)


def create_dataset(
    record: int,
    dataset: int,
    value: bytes,
) -> bytes:

    if len(value) > 0x7FFF:
        raise ValueError(
            "Use extended dataset."
        )

    return (
        bytes(
            (
                0x1C,
                record,
                dataset,
            )
        )
        + len(value).to_bytes(
            2,
            "big",
        )
        + value
    )


def create_extended_dataset(
    record: int,
    dataset: int,
    value: bytes,
) -> bytes:

    value_length = len(value)

    length_bytes = (
        value_length.to_bytes(
            max(
                1,
                (
                    value_length.bit_length()
                    + 7
                ) // 8,
            ),
            "big",
        )
    )

    descriptor = (
        0x8000
        | len(length_bytes)
    )

    return (
        bytes(
            (
                0x1C,
                record,
                dataset,
            )
        )
        + descriptor.to_bytes(
            2,
            "big",
        )
        + length_bytes
        + value
    )


def create_iptc_data() -> bytes:

    return b"".join(
        (
            create_dataset(
                1,
                90,
                IPTC_UTF8_DESIGNATOR,
            ),

            create_dataset(
                2,
                5,
                "Baluarte de Santiago".encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                25,
                "Veracruz".encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                25,
                "fortaleza histórica".encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                80,
                "María López".encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                90,
                "Veracruz".encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                92,
                (
                    "Baluarte de Santiago"
                ).encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                95,
                "Veracruz".encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                100,
                b"MEX",
            ),

            create_dataset(
                2,
                101,
                "México".encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                105,
                (
                    "Fortaleza histórica "
                    "en Veracruz"
                ).encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                116,
                (
                    "Copyright Test News"
                ).encode(
                    "utf-8"
                ),
            ),

            create_dataset(
                2,
                120,
                (
                    "Fotografía editorial "
                    "de prueba."
                ).encode(
                    "utf-8"
                ),
            ),
        )
    )


def create_resource(
    resource_id: int,
    data: bytes,
    name: bytes = b"",
) -> bytes:

    if len(name) > 255:
        raise ValueError(
            "Pascal name too long."
        )

    result = bytearray()

    result += b"8BIM"

    result += resource_id.to_bytes(
        2,
        "big",
    )

    result += bytes(
        (
            len(name),
        )
    )

    result += name

    if (
        (1 + len(name))
        % 2
        != 0
    ):
        result += b"\x00"

    result += len(data).to_bytes(
        4,
        "big",
    )

    result += data

    if len(data) % 2:
        result += b"\x00"

    return bytes(
        result
    )


def create_app13_segment() -> JpegSegment:

    iptc = create_iptc_data()

    #
    # Incluimos primero un recurso
    # Photoshop distinto para comprobar
    # que el parser busca específicamente
    # 0x0404.
    #
    resources = (
        create_resource(
            0x040A,
            b"\x01",
        )
        + create_resource(
            IPTC_RESOURCE_ID,
            iptc,
        )
    )

    payload = (
        PHOTOSHOP_IDENTIFIER
        + resources
    )

    return JpegSegment(
        offset=2,
        marker=0xED,
        name="APP13",
        declared_length=(
            len(payload) + 2
        ),
        payload_length=len(payload),
        is_exif=False,
        payload=payload,
    )


def create_jpeg_with_iptc() -> bytes:

    segment = (
        create_app13_segment()
    )

    return (
        b"\xFF\xD8"
        + b"\xFF\xED"
        + (
            len(segment.payload)
            + 2
        ).to_bytes(
            2,
            "big",
        )
        + segment.payload
        + b"\xFF\xDA"
        + b"\x00\x02"
    )


class TestIptcParser(
    unittest.TestCase
):

    def test_detects_photoshop_app13(
        self,
    ):

        self.assertTrue(
            is_photoshop_app13(
                create_app13_segment()
            )
        )

    def test_parses_photoshop_resources(
        self,
    ):

        resources = (
            parse_photoshop_resources(
                create_app13_segment()
            )
        )

        self.assertEqual(
            len(resources),
            2,
        )

        self.assertEqual(
            resources[0].resource_id,
            0x040A,
        )

        self.assertEqual(
            resources[1].resource_id,
            IPTC_RESOURCE_ID,
        )

    def test_extracts_iptc_resource(
        self,
    ):

        resource = (
            extract_iptc_resource(
                create_app13_segment()
            )
        )

        self.assertIsNotNone(
            resource
        )

        assert resource is not None

        self.assertTrue(
            resource.startswith(
                b"\x1C"
            )
        )

    def test_extracts_common_fields(
        self,
    ):

        metadata = parse_iptc_iim(
            create_iptc_data()
        )

        self.assertEqual(
            metadata.title,
            "Baluarte de Santiago",
        )

        self.assertEqual(
            metadata.creator,
            "María López",
        )

        self.assertEqual(
            metadata.headline,
            (
                "Fortaleza histórica "
                "en Veracruz"
            ),
        )

        self.assertEqual(
            metadata.caption,
            (
                "Fotografía editorial "
                "de prueba."
            ),
        )

        self.assertEqual(
            metadata.copyright,
            "Copyright Test News",
        )

    def test_extracts_repeated_keywords(
        self,
    ):

        metadata = parse_iptc_iim(
            create_iptc_data()
        )

        self.assertEqual(
            metadata.keywords,
            (
                "Veracruz",
                "fortaleza histórica",
            ),
        )

    def test_extracts_location_fields(
        self,
    ):

        metadata = parse_iptc_iim(
            create_iptc_data()
        )

        self.assertEqual(
            metadata.sublocation,
            "Baluarte de Santiago",
        )

        self.assertEqual(
            metadata.city,
            "Veracruz",
        )

        self.assertEqual(
            metadata.province_state,
            "Veracruz",
        )

        self.assertEqual(
            metadata.country_code,
            "MEX",
        )

        self.assertEqual(
            metadata.country,
            "México",
        )

    def test_detects_utf8_charset(
        self,
    ):

        metadata = parse_iptc_iim(
            create_iptc_data()
        )

        self.assertEqual(
            metadata.encoding,
            "utf-8",
        )

        self.assertEqual(
            metadata.get(
                "CodedCharacterSet"
            ),
            "UTF-8",
        )

    def test_supports_extended_dataset_length(
        self,
    ):

        value = (
            b"A" * 33000
        )

        data = (
            create_extended_dataset(
                2,
                200,
                value,
            )
        )

        metadata = parse_iptc_iim(
            data
        )

        self.assertEqual(
            len(
                metadata.datasets
            ),
            1,
        )

        self.assertEqual(
            metadata.datasets[
                0
            ].raw_value,
            value,
        )

    def test_extracts_from_jpeg_file(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "iptc.jpg"
            )

            path.write_bytes(
                create_jpeg_with_iptc()
            )

            metadata = (
                extract_iptc_from_jpeg(
                    path
                )
            )

        self.assertIsNotNone(
            metadata
        )

        assert metadata is not None

        self.assertEqual(
            metadata.creator,
            "María López",
        )

        self.assertEqual(
            metadata.city,
            "Veracruz",
        )

    def test_returns_none_without_iptc(
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
                / "no-iptc.jpg"
            )

            path.write_bytes(
                jpeg
            )

            metadata = (
                extract_iptc_from_jpeg(
                    path
                )
            )

        self.assertIsNone(
            metadata
        )

    def test_rejects_truncated_dataset(
        self,
    ):

        data = (
            b"\x1C"
            b"\x02"
            b"\x78"
            b"\x00\x10"
            b"short"
        )

        with self.assertRaises(
            IptcParserError
        ):
            parse_iptc_iim(
                data
            )


if __name__ == "__main__":
    unittest.main()
