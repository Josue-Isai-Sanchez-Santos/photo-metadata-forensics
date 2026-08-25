import tempfile
import unittest
from pathlib import Path

from photometa.analysis.privacy import (
    PrivacyContext,
    analyze_privacy,
    analyze_privacy_context,
)
from photometa.presentation.privacy import (
    format_privacy_detailed_report,
    format_privacy_report,
)


class TestPrivacyAnalysis(
    unittest.TestCase
):

    def test_detects_gps_coordinates_and_altitude(
        self,
    ):

        context = PrivacyContext(
            gps={
                "GPSLatitude": (
                    19,
                    11,
                    54,
                ),
                "GPSLongitude": (
                    96,
                    8,
                    1,
                ),
                "GPSAltitude": 7.8,
            }
        )

        report = (
            analyze_privacy_context(
                context
            )
        )

        self.assertTrue(
            report.has(
                "gps_coordinates"
            )
        )

        self.assertTrue(
            report.has(
                "gps_altitude"
            )
        )

    def test_detects_capture_date_and_device_model(
        self,
    ):

        context = PrivacyContext(
            ifd0={
                "Model": (
                    "Test Phone"
                ),
            },
            exif={
                "DateTimeOriginal": (
                    "2026:08:24 12:00:00"
                ),
            },
        )

        report = (
            analyze_privacy_context(
                context
            )
        )

        self.assertTrue(
            report.has(
                "device_model"
            )
        )

        self.assertTrue(
            report.has(
                "original_capture_date"
            )
        )

    def test_detects_serial_owner_software_and_unique_id(
        self,
    ):

        context = PrivacyContext(
            ifd0={
                "Artist": "Alice",
                "Software": (
                    "Photo Editor"
                ),
                "Copyright": (
                    "Alice 2026"
                ),
            },
            exif={
                "CameraOwnerName": (
                    "Alice"
                ),
                "BodySerialNumber": (
                    "ABC123"
                ),
                "LensSerialNumber": (
                    "LENS987"
                ),
                "ImageUniqueID": (
                    "unique-image-id"
                ),
            },
        )

        report = (
            analyze_privacy_context(
                context
            )
        )

        self.assertTrue(
            report.has(
                "serial_number"
            )
        )

        self.assertTrue(
            report.has(
                "owner_information"
            )
        )

        self.assertTrue(
            report.has(
                "software"
            )
        )

        self.assertTrue(
            report.has(
                "copyright_author"
            )
        )

        self.assertTrue(
            report.has(
                "unique_identifier"
            )
        )

    def test_detects_xmp_location_and_identifiers(
        self,
    ):

        context = PrivacyContext(
            xmp={
                "xmpMM:DocumentID": (
                    "xmp.did:12345"
                ),
                "photoshop:City": (
                    "Veracruz"
                ),
                "dc:creator": (
                    "Alice",
                ),
                "xmp:CreatorTool": (
                    "Adobe Photoshop"
                ),
            }
        )

        report = (
            analyze_privacy_context(
                context
            )
        )

        self.assertTrue(
            report.has(
                "unique_identifier"
            )
        )

        self.assertTrue(
            report.has(
                "editorial_location"
            )
        )

        self.assertTrue(
            report.has(
                "owner_information"
            )
        )

        self.assertTrue(
            report.has(
                "software"
            )
        )

    def test_detects_iptc_location(
        self,
    ):

        context = PrivacyContext(
            iptc={
                "Creator": (
                    "News Photographer",
                ),
                "City": "Veracruz",
                "CountryName": "Mexico",
            }
        )

        report = (
            analyze_privacy_context(
                context
            )
        )

        self.assertTrue(
            report.has(
                "editorial_location"
            )
        )

        self.assertTrue(
            report.has(
                "owner_information"
            )
        )

    def test_empty_context_has_no_findings(
        self,
    ):

        report = (
            analyze_privacy_context(
                PrivacyContext()
            )
        )

        self.assertFalse(
            report.has_findings
        )

        self.assertEqual(
            report.count,
            0,
        )

    def test_formats_privacy_report(
        self,
    ):

        report = (
            analyze_privacy_context(
                PrivacyContext(
                    ifd0={
                        "Model": (
                            "Test Phone"
                        ),
                    },
                    exif={
                        "DateTimeOriginal": (
                            "2026:08:24 "
                            "12:00:00"
                        ),
                    },
                )
            )
        )

        text = format_privacy_report(
            report
        )

        detailed = (
            format_privacy_detailed_report(
                report
            )
        )

        self.assertIn(
            "PRIVACY ANALYSIS",
            text,
        )

        self.assertIn(
            "Device model exposed",
            text,
        )

        self.assertIn(
            "Original capture date exposed",
            text,
        )

        self.assertIn(
            "[MEDIUM]",
            detailed,
        )

        self.assertIn(
            "Source:",
            detailed,
        )

    def test_analyzes_jpeg_without_metadata(
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
                / "empty.jpg"
            )

            path.write_bytes(
                jpeg
            )

            report = analyze_privacy(
                path
            )

        self.assertFalse(
            report.has_findings
        )


if __name__ == "__main__":
    unittest.main()
