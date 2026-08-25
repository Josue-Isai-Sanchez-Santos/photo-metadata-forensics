import tempfile
import unittest
from pathlib import Path

from photometa.parsers.jpeg import (
    JpegSegment,
)
from photometa.parsers.xmp import (
    XMP_IDENTIFIER,
    XmpParserError,
    extract_xmp_from_jpeg,
    is_xmp_segment,
    parse_xmp_segment,
)


def create_xmp_xml() -> bytes:

    return b'''<?xpacket begin=""?>
<x:xmpmeta
    xmlns:x="adobe:ns:meta/">
  <rdf:RDF
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

    <rdf:Description
        rdf:about=""
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/"
        xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
        xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
        xmp:CreatorTool="Adobe Photoshop Lightroom Classic"
        xmp:Rating="5"
        xmp:CreateDate="2026-08-11T14:32:51-06:00"
        xmp:ModifyDate="2026-08-11T15:10:00-06:00"
        xmp:MetadataDate="2026-08-11T15:10:10-06:00"
        photoshop:DateCreated="2026-08-11T14:32:51-06:00"
        crs:ProcessVersion="15.4">

      <dc:creator>
        <rdf:Seq>
          <rdf:li>Test Creator</rdf:li>
          <rdf:li>Second Creator</rdf:li>
        </rdf:Seq>
      </dc:creator>

      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang="es">
            Puerto de Veracruz ES
          </rdf:li>
          <rdf:li xml:lang="x-default">
            Puerto de Veracruz
          </rdf:li>
        </rdf:Alt>
      </dc:title>

      <dc:description>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">
            Fotografia procesada de prueba
          </rdf:li>
        </rdf:Alt>
      </dc:description>

    </rdf:Description>

  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''


def create_xmp_segment() -> JpegSegment:

    payload = (
        XMP_IDENTIFIER
        + create_xmp_xml()
    )

    return JpegSegment(
        offset=2,
        marker=0xE1,
        name="APP1",
        declared_length=(
            len(payload) + 2
        ),
        payload_length=len(payload),
        is_exif=False,
        payload=payload,
    )


def create_exif_segment() -> JpegSegment:

    payload = (
        b"Exif\x00\x00"
        b"dummy"
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
        XMP_IDENTIFIER
        + create_xmp_xml()
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


class TestXmpParser(unittest.TestCase):

    def test_detects_xmp_app1(
        self,
    ):

        self.assertTrue(
            is_xmp_segment(
                create_xmp_segment()
            )
        )

    def test_does_not_confuse_exif_with_xmp(
        self,
    ):

        self.assertFalse(
            is_xmp_segment(
                create_exif_segment()
            )
        )

    def test_extracts_common_properties(
        self,
    ):

        metadata = parse_xmp_segment(
            create_xmp_segment()
        )

        self.assertEqual(
            metadata.creator_tool,
            (
                "Adobe Photoshop "
                "Lightroom Classic"
            ),
        )

        self.assertEqual(
            metadata.rating,
            5,
        )

        self.assertEqual(
            metadata.create_date,
            "2026-08-11T14:32:51-06:00",
        )

        self.assertEqual(
            metadata.modify_date,
            "2026-08-11T15:10:00-06:00",
        )

        self.assertEqual(
            metadata.metadata_date,
            "2026-08-11T15:10:10-06:00",
        )

        self.assertEqual(
            metadata.get(
                "photoshop:DateCreated"
            ),
            "2026-08-11T14:32:51-06:00",
        )

        self.assertEqual(
            metadata.get(
                "crs:ProcessVersion"
            ),
            "15.4",
        )

    def test_extracts_creator_sequence(
        self,
    ):

        metadata = parse_xmp_segment(
            create_xmp_segment()
        )

        self.assertEqual(
            metadata.creator,
            (
                "Test Creator",
                "Second Creator",
            ),
        )

    def test_prefers_x_default_title(
        self,
    ):

        metadata = parse_xmp_segment(
            create_xmp_segment()
        )

        self.assertEqual(
            metadata.title,
            "Puerto de Veracruz",
        )

        self.assertEqual(
            metadata.description,
            (
                "Fotografia procesada "
                "de prueba"
            ),
        )

    def test_extracts_xmp_from_jpeg_file(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "xmp.jpg"
            )

            path.write_bytes(
                create_jpeg_bytes()
            )

            metadata = (
                extract_xmp_from_jpeg(
                    path
                )
            )

        self.assertIsNotNone(
            metadata
        )

        assert metadata is not None

        self.assertEqual(
            metadata.rating,
            5,
        )

    def test_returns_none_when_xmp_missing(
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
                / "no-xmp.jpg"
            )

            path.write_bytes(
                jpeg
            )

            metadata = (
                extract_xmp_from_jpeg(
                    path
                )
            )

        self.assertIsNone(
            metadata
        )

    def test_rejects_invalid_xml(
        self,
    ):

        payload = (
            XMP_IDENTIFIER
            + b"<x:xmpmeta>"
        )

        segment = JpegSegment(
            offset=2,
            marker=0xE1,
            name="APP1",
            declared_length=(
                len(payload) + 2
            ),
            payload_length=len(payload),
            is_exif=False,
            payload=payload,
        )

        with self.assertRaises(
            XmpParserError
        ):
            parse_xmp_segment(
                segment
            )

    def test_maps_google_camera_namespace(
        self,
    ):

        xml = b'''<x:xmpmeta
            xmlns:x="adobe:ns:meta/">
          <rdf:RDF
              xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

            <rdf:Description
                rdf:about=""
                xmlns:gcamera="http://ns.google.com/photos/1.0/camera/"
                gcamera:ImageType="HDR"
                gcamera:ZComment="Test camera data">
            </rdf:Description>

          </rdf:RDF>
        </x:xmpmeta>'''

        payload = (
            XMP_IDENTIFIER
            + xml
        )

        segment = JpegSegment(
            offset=2,
            marker=0xE1,
            name="APP1",
            declared_length=(
                len(payload) + 2
            ),
            payload_length=len(payload),
            is_exif=False,
            payload=payload,
        )

        metadata = parse_xmp_segment(
            segment
        )

        self.assertEqual(
            metadata.get(
                "gcamera:ImageType"
            ),
            "HDR",
        )

        self.assertEqual(
            metadata.get(
                "gcamera:ZComment"
            ),
            "Test camera data",
        )

if __name__ == "__main__":
    unittest.main()
