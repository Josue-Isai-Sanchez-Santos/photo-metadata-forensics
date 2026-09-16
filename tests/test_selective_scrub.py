import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from photometa.analysis.privacy import (
    analyze_privacy,
)
from photometa.extractors.exif_ifd import (
    extract_exif_ifd_from_jpeg,
)
from photometa.extractors.ifd0 import (
    extract_ifd0_from_jpeg,
)
from photometa.parsers.iptc import (
    extract_iptc_from_jpeg,
)
from photometa.parsers.xmp import (
    XMP_IDENTIFIER,
    extract_xmp_from_jpeg,
)
from photometa.sanitization.scrub import (
    ScrubError,
)
from photometa.sanitization.selective import (
    SCRUB_MODE_GPS,
    SCRUB_MODE_PRIVACY,
    scrub_jpeg_selective,
)
from tests.test_exif_ifd import (
    build_exif_tiff,
)
from tests.test_ifd0 import (
    create_tiff_data,
)
from tests.test_iptc import (
    create_app13_segment,
)
from tests.test_scrub import (
    create_jpeg,
    gps_exif_segment,
    segment,
)


def exif_segment_from_tiff(
    tiff: bytes,
) -> bytes:

    return segment(
        0xE1,
        (
            b"Exif\x00\x00"
            + tiff
        ),
    )


def xmp_segment() -> bytes:

    xml = b'''<x:xmpmeta
xmlns:x="adobe:ns:meta/"
xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:dc="http://purl.org/dc/elements/1.1/"
xmlns:xmp="http://ns.adobe.com/xap/1.0/"
xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"
xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
xmlns:exif="http://ns.adobe.com/exif/1.0/">
<rdf:RDF>
<rdf:Description
rdf:about=""
xmpMM:DocumentID="xmp.did:12345"
photoshop:City="Veracruz"
exif:GPSLatitude="19.1"
exif:GPSLongitude="-96.1"
xmp:CreatorTool="Photo Editor">
<dc:title>
<rdf:Alt>
<rdf:li xml:lang="x-default">Public title</rdf:li>
</rdf:Alt>
</dc:title>
<dc:creator>
<rdf:Seq>
<rdf:li>Alice</rdf:li>
</rdf:Seq>
</dc:creator>
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>'''

    return segment(
        0xE1,
        XMP_IDENTIFIER
        + xml,
    )


def iptc_segment() -> bytes:

    app13 = (
        create_app13_segment()
    )

    return segment(
        0xED,
        app13.payload,
    )


class TestSelectiveScrub(
    unittest.TestCase
):

    def test_gps_mode_removes_gps_but_preserves_exif(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "gps-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        gps_exif_segment(),
                    )
                )
            )

            report = (
                scrub_jpeg_selective(
                    path,
                    output,
                    mode=SCRUB_MODE_GPS,
                )
            )

            self.assertTrue(
                report.original_gps
            )

            self.assertFalse(
                report.sanitized_gps
            )

            self.assertIn(
                b"Exif\x00\x00",
                output.read_bytes(),
            )

            self.assertTrue(
                report.image_data_preserved
            )

    def test_gps_mode_removes_xmp_gps_but_preserves_creator(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "gps-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        xmp_segment(),
                    )
                )
            )

            scrub_jpeg_selective(
                path,
                output,
                mode=SCRUB_MODE_GPS,
            )

            metadata = (
                extract_xmp_from_jpeg(
                    output
                )
            )

            self.assertIsNotNone(
                metadata
            )

            assert metadata is not None

            self.assertEqual(
                metadata.title,
                "Public title",
            )

            self.assertEqual(
                metadata.creator,
                (
                    "Alice",
                ),
            )

            self.assertIsNone(
                metadata.get(
                    "exif:GPSLatitude"
                )
            )

            self.assertIsNone(
                metadata.get(
                    "exif:GPSLongitude"
                )
            )

            self.assertEqual(
                metadata.get(
                    "xmpMM:DocumentID"
                ),
                "xmp.did:12345",
            )

    def test_gps_mode_preserves_iptc_location(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "gps-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        iptc_segment(),
                    )
                )
            )

            scrub_jpeg_selective(
                path,
                output,
                mode=SCRUB_MODE_GPS,
            )

            metadata = (
                extract_iptc_from_jpeg(
                    output
                )
            )

            self.assertIsNotNone(
                metadata
            )

            assert metadata is not None

            self.assertEqual(
                metadata.city,
                "Veracruz",
            )

            self.assertEqual(
                metadata.creator,
                "María López",
            )

    def test_privacy_mode_preserves_non_sensitive_ifd0(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "privacy-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        exif_segment_from_tiff(
                            create_tiff_data()
                        ),
                    )
                )
            )

            scrub_jpeg_selective(
                path,
                output,
                mode=SCRUB_MODE_PRIVACY,
            )

            metadata = (
                extract_ifd0_from_jpeg(
                    output
                )
            )

            self.assertIsNone(
                metadata.get(
                    "Model"
                )
            )

            self.assertIsNone(
                metadata.get(
                    "Software"
                )
            )

            self.assertIsNone(
                metadata.get(
                    "Copyright"
                )
            )

            self.assertEqual(
                metadata.get(
                    "Make"
                ),
                "Samsung",
            )

            self.assertEqual(
                metadata.get(
                    "ImageDescription"
                ),
                "Sample photo",
            )

    def test_privacy_mode_removes_original_date_but_preserves_exposure(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "privacy-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        exif_segment_from_tiff(
                            build_exif_tiff()
                        ),
                    )
                )
            )

            scrub_jpeg_selective(
                path,
                output,
                mode=SCRUB_MODE_PRIVACY,
            )

            metadata = (
                extract_exif_ifd_from_jpeg(
                    output
                )
            )

            self.assertIsNone(
                metadata.get(
                    "DateTimeOriginal"
                )
            )

            self.assertEqual(
                metadata.get(
                    "ExposureTime"
                ),
                Fraction(
                    1,
                    120,
                ),
            )

            self.assertEqual(
                metadata.get(
                    "LensModel"
                ),
                "REDMAGIC Camera",
            )

    def test_privacy_mode_sanitizes_xmp_but_preserves_title(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "privacy-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        xmp_segment(),
                    )
                )
            )

            scrub_jpeg_selective(
                path,
                output,
                mode=SCRUB_MODE_PRIVACY,
            )

            metadata = (
                extract_xmp_from_jpeg(
                    output
                )
            )

            self.assertIsNotNone(
                metadata
            )

            assert metadata is not None

            self.assertEqual(
                metadata.title,
                "Public title",
            )

            self.assertEqual(
                metadata.creator,
                (),
            )

            self.assertIsNone(
                metadata.get(
                    "dc:creator"
                )
            )

            self.assertIsNone(
                metadata.creator_tool
            )

            self.assertIsNone(
                metadata.get(
                    "xmpMM:DocumentID"
                )
            )

            self.assertIsNone(
                metadata.get(
                    "photoshop:City"
                )
            )

    def test_privacy_mode_sanitizes_iptc_but_preserves_editorial_content(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "privacy-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        iptc_segment(),
                    )
                )
            )

            scrub_jpeg_selective(
                path,
                output,
                mode=SCRUB_MODE_PRIVACY,
            )

            metadata = (
                extract_iptc_from_jpeg(
                    output
                )
            )

            self.assertIsNotNone(
                metadata
            )

            assert metadata is not None

            self.assertEqual(
                metadata.title,
                "Baluarte de Santiago",
            )

            self.assertEqual(
                metadata.headline,
                (
                    "Fortaleza histórica "
                    "en Veracruz"
                ),
            )

            self.assertIn(
                "Veracruz",
                metadata.keywords,
            )

            self.assertIsNone(
                metadata.creator
            )

            self.assertIsNone(
                metadata.city
            )

            self.assertIsNone(
                metadata.sublocation
            )

            self.assertIsNone(
                metadata.country
            )

            self.assertIsNone(
                metadata.copyright
            )

    def test_privacy_mode_reaches_zero_supported_findings(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "privacy-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        exif_segment_from_tiff(
                            create_tiff_data()
                        ),
                        xmp_segment(),
                        iptc_segment(),
                    )
                )
            )

            before = analyze_privacy(
                path
            )

            report = (
                scrub_jpeg_selective(
                    path,
                    output,
                    mode=SCRUB_MODE_PRIVACY,
                )
            )

            after = analyze_privacy(
                output
            )

            self.assertGreater(
                before.count,
                0,
            )

            self.assertEqual(
                after.count,
                0,
            )

            self.assertEqual(
                report.privacy_findings_after,
                0,
            )

    def test_selective_scrub_preserves_original_and_image_data(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output = (
                Path(temp_dir)
                / "privacy-clean.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        xmp_segment(),
                    )
                )
            )

            original = (
                path.read_bytes()
            )

            report = (
                scrub_jpeg_selective(
                    path,
                    output,
                    mode=SCRUB_MODE_PRIVACY,
                )
            )

            self.assertEqual(
                path.read_bytes(),
                original,
            )

            self.assertTrue(
                report.original_unchanged
            )

            self.assertTrue(
                report.image_data_preserved
            )

            self.assertTrue(
                report.dimensions_preserved
            )

    def test_rejects_unknown_selective_mode(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            path.write_bytes(
                create_jpeg()
            )

            with self.assertRaises(
                ScrubError
            ):

                scrub_jpeg_selective(
                    path,
                    mode="unknown",
                )


if __name__ == "__main__":
    unittest.main()
