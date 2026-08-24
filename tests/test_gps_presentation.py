import unittest
from fractions import Fraction

from photometa.extractors.gps_ifd import (
    GpsMetadata,
    GpsMetadataEntry,
    build_location_summary,
    extract_gps_ifd_metadata,
)
from photometa.parsers.exif import (
    parse_exif,
)
from photometa.presentation.gps import (
    format_gps_raw_report,
    format_location_report,
)
from tests.test_gps_ifd import (
    create_exif_segment,
)


class TestGpsPresentation(
    unittest.TestCase
):

    def test_formats_human_location_report(
        self,
    ):

        metadata = (
            extract_gps_ifd_metadata(
                parse_exif(
                    create_exif_segment()
                )
            )
        )

        summary = build_location_summary(
            metadata
        )

        report = format_location_report(
            summary
        )

        self.assertIn(
            "Latitude:       19.432608",
            report,
        )

        self.assertIn(
            "Longitude:      -99.133209",
            report,
        )

        self.assertIn(
            "Altitude:       2240 m "
            "(EXIF reports above sea level)",
            report,
        )

        self.assertNotIn(
            "Fraction(",
            report,
        )

    def test_formats_forensic_rationals(
        self,
    ):

        metadata = (
            extract_gps_ifd_metadata(
                parse_exif(
                    create_exif_segment()
                )
            )
        )

        report = format_gps_raw_report(
            metadata
        )

        self.assertIn(
            "(19/1, 25/1, 35868/625)",
            report,
        )

        self.assertIn(
            "2240/1",
            report,
        )

        self.assertNotIn(
            "Fraction(",
            report,
        )

    def test_reports_below_sea_level(
        self,
    ):

        metadata = GpsMetadata(
            offset=817,
            entries=(
                GpsMetadataEntry(
                    tag=0x0005,
                    tag_name="GPSAltitudeRef",
                    field_type=1,
                    field_type_name="BYTE",
                    count=1,
                    value=1,
                ),
                GpsMetadataEntry(
                    tag=0x0006,
                    tag_name="GPSAltitude",
                    field_type=5,
                    field_type_name="RATIONAL",
                    count=1,
                    value=Fraction(
                        1953,
                        250,
                    ),
                ),
            ),
        )

        summary = build_location_summary(
            metadata
        )

        self.assertEqual(
            summary.altitude,
            -7.812,
        )

        self.assertEqual(
            summary.altitude_ref,
            1,
        )

        self.assertEqual(
            summary.altitude_reference,
            "below sea level",
        )

        report = format_location_report(
            summary
        )

        self.assertIn(
            "Altitude:       -7.812 m "
            "(EXIF reports below sea level)",
            report,
        )


if __name__ == "__main__":
    unittest.main()
