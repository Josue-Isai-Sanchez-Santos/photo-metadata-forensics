import tempfile
import unittest
from pathlib import Path

from photometa.analysis.anomalies import (
    AnomalyContext,
    analyze_anomalies,
    analyze_anomaly_context,
)
from photometa.presentation.anomalies import (
    format_anomaly_report,
)
from tests.test_scrub import (
    create_jpeg,
    segment,
)


def make_context(
    **kwargs,
) -> AnomalyContext:

    values = {
        "jpeg_width": 4000,
        "jpeg_height": 3000,
    }

    values.update(
        kwargs
    )

    return AnomalyContext(
        **values
    )


def little_u16(
    value: int,
) -> bytes:

    return value.to_bytes(
        2,
        "little",
    )


def little_u32(
    value: int,
) -> bytes:

    return value.to_bytes(
        4,
        "little",
    )


def duplicate_model_tiff() -> bytes:

    tiff = bytearray()

    tiff += b"II"
    tiff += b"\x2A\x00"
    tiff += little_u32(
        8
    )

    #
    # IFD0 with duplicate Model.
    #
    tiff += little_u16(
        2
    )

    for value in (
        b"A\x00",
        b"B\x00",
    ):

        tiff += little_u16(
            0x0110
        )

        tiff += little_u16(
            2
        )

        tiff += little_u32(
            len(value)
        )

        tiff += value.ljust(
            4,
            b"\x00",
        )

    tiff += b"\x00\x00\x00\x00"

    return bytes(
        tiff
    )


def suspicious_offset_tiff() -> bytes:

    tiff = bytearray()

    tiff += b"II"
    tiff += b"\x2A\x00"
    tiff += little_u32(
        8
    )

    tiff += little_u16(
        1
    )

    #
    # ImageDescription:
    # ASCII count=10.
    #
    # Because 10 > 4, Value/Offset is an
    # offset. We intentionally point it to
    # byte 4, inside the TIFF header.
    #
    tiff += little_u16(
        0x010E
    )

    tiff += little_u16(
        2
    )

    tiff += little_u32(
        10
    )

    tiff += little_u32(
        4
    )

    tiff += b"\x00\x00\x00\x00"

    return bytes(
        tiff
    )


def jpeg_with_exif_tiff(
    tiff: bytes,
) -> bytes:

    return create_jpeg(
        (
            segment(
                0xE1,
                (
                    b"Exif\x00\x00"
                    + tiff
                ),
            ),
        )
    )


class TestAnomalyAnalysis(
    unittest.TestCase
):

    def test_empty_context_has_no_anomalies(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context()
            )
        )

        self.assertFalse(
            report.has_findings
        )

    def test_datetime_difference(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    ifd0={
                        "DateTime":
                        (
                            "2026:09:03 "
                            "13:00:00"
                        ),
                    },
                    exif={
                        "DateTimeOriginal":
                        (
                            "2026:09:03 "
                            "12:00:00"
                        ),
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "datetime_differs"
            )
        )

    def test_original_datetime_after_datetime(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    ifd0={
                        "DateTime":
                        (
                            "2026:09:03 "
                            "11:00:00"
                        ),
                    },
                    exif={
                        "DateTimeOriginal":
                        (
                            "2026:09:03 "
                            "12:00:00"
                        ),
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "datetime_order_inconsistent"
            )
        )

        self.assertFalse(
            report.has(
                "datetime_differs"
            )
        )

    def test_invalid_datetime_format(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    ifd0={
                        "DateTime":
                        "2026-09-03 12:00:00",
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "datetime_format_invalid"
            )
        )

    def test_gps_without_datestamp(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    gps={
                        "GPSLatitude":
                        (
                            19,
                            11,
                            30,
                        ),
                        "GPSLatitudeRef":
                        "N",
                        "GPSLongitude":
                        (
                            96,
                            8,
                            0,
                        ),
                        "GPSLongitudeRef":
                        "W",
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "gps_datestamp_missing"
            )
        )

    def test_gps_missing_reference(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    gps={
                        "GPSLatitude":
                        (
                            19,
                            11,
                            30,
                        ),
                        "GPSLongitude":
                        (
                            96,
                            8,
                            0,
                        ),
                        "GPSDateStamp":
                        "2026:09:03",
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "gps_reference_missing"
            )
        )

    def test_exif_dimensions_mismatch(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    jpeg_width=1600,
                    jpeg_height=1200,
                    exif={
                        "PixelXDimension":
                        4000,
                        "PixelYDimension":
                        3000,
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "exif_dimensions_mismatch"
            )
        )

    def test_ifd0_dimensions_mismatch(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    jpeg_width=1600,
                    jpeg_height=1200,
                    ifd0={
                        "ImageWidth":
                        4000,
                        "ImageLength":
                        3000,
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "ifd0_dimensions_mismatch"
            )
        )

    def test_known_editing_software(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    ifd0={
                        "Software":
                        (
                            "Adobe Photoshop "
                            "27.0"
                        ),
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "editing_software_present"
            )
        )

    def test_camera_software_is_not_automatically_anomalous(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    ifd0={
                        "Software":
                        "nubia Camera",
                    },
                )
            )
        )

        self.assertFalse(
            report.has(
                "editing_software_present"
            )
        )

    def test_incomplete_make_model_pair(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    ifd0={
                        "Make":
                        "nubia",
                    },
                )
            )
        )

        self.assertTrue(
            report.has(
                "make_model_incomplete"
            )
        )

    def test_multiple_exif_segments(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    exif_segment_count=2
                )
            )
        )

        self.assertTrue(
            report.has(
                "multiple_exif_segments"
            )
        )

    def test_detects_declared_but_corrupt_exif(
        self,
    ):

        jpeg = create_jpeg(
            (
                segment(
                    0xE1,
                    (
                        b"Exif\x00\x00"
                        b"broken"
                    ),
                ),
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "corrupt.jpg"
            )

            path.write_bytes(
                jpeg
            )

            report = (
                analyze_anomalies(
                    path
                )
            )

            self.assertTrue(
                report.has(
                    "exif_structure_corrupt"
                )
            )

    def test_detects_duplicate_tags(
        self,
    ):

        jpeg = (
            jpeg_with_exif_tiff(
                duplicate_model_tiff()
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "duplicate.jpg"
            )

            path.write_bytes(
                jpeg
            )

            report = (
                analyze_anomalies(
                    path
                )
            )

            self.assertTrue(
                report.has(
                    "duplicate_tag"
                )
            )

    def test_detects_suspicious_offset(
        self,
    ):

        jpeg = (
            jpeg_with_exif_tiff(
                suspicious_offset_tiff()
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "offset.jpg"
            )

            path.write_bytes(
                jpeg
            )

            report = (
                analyze_anomalies(
                    path
                )
            )

            self.assertTrue(
                report.has(
                    "suspicious_offset"
                )
            )

    def test_simple_jpeg_has_no_anomalies(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "clean.jpg"
            )

            path.write_bytes(
                create_jpeg()
            )

            report = (
                analyze_anomalies(
                    path
                )
            )

            self.assertFalse(
                report.has_findings
            )

    def test_formatter_contains_disclaimer(
        self,
    ):

        report = (
            analyze_anomaly_context(
                make_context(
                    ifd0={
                        "Software":
                        "Adobe Photoshop",
                    },
                )
            )
        )

        text = (
            format_anomaly_report(
                report
            )
        )

        self.assertIn(
            "ANOMALIES",
            text,
        )

        self.assertIn(
            (
                "Software metadata "
                "references"
            ),
            text,
        )

        self.assertIn(
            (
                "This does not prove "
                "image manipulation."
            ),
            text,
        )


if __name__ == "__main__":
    unittest.main()
