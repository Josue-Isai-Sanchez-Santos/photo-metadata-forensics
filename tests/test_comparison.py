import tempfile
import unittest
from pathlib import Path

from photometa.analysis.comparison import (
    RECOMPRESSION_LIKELY,
    RECOMPRESSION_NONE,
    RECOMPRESSION_POSSIBLE,
    compare_images,
)
from photometa.parsers.xmp import (
    XMP_IDENTIFIER,
)
from photometa.presentation.comparison import (
    format_comparison_report,
)
from tests.test_gps_ifd import (
    build_gps_tiff,
)
from tests.test_ifd0 import (
    create_tiff_data,
)


def segment(
    marker: int,
    payload: bytes,
) -> bytes:

    return (
        b"\xFF"
        + bytes(
            (marker,)
        )
        + (
            len(payload) + 2
        ).to_bytes(
            2,
            "big",
        )
        + payload
    )


def exif_segment(
    tiff: bytes,
) -> bytes:

    return segment(
        0xE1,
        b"Exif\x00\x00"
        + tiff,
    )


def gps_segment() -> bytes:

    return exif_segment(
        build_gps_tiff()
    )


def model_segment() -> bytes:

    return exif_segment(
        create_tiff_data()
    )


def xmp_segment() -> bytes:

    return segment(
        0xE1,
        XMP_IDENTIFIER
        + b"<x:xmpmeta/>",
    )


def create_jpeg(
    *,
    width: int = 32,
    height: int = 16,
    app_segments: tuple[
        bytes,
        ...
    ] = (),
    quantization_value: int = 5,
    scan_data: bytes = (
        b"\x11\x22\x33"
    ),
) -> bytes:

    dqt_payload = (
        b"\x00"
        + bytes(
            [quantization_value]
        )
        * 64
    )

    sof_payload = (
        b"\x08"
        + height.to_bytes(
            2,
            "big",
        )
        + width.to_bytes(
            2,
            "big",
        )
        + b"\x01"
        + b"\x01\x11\x00"
    )

    sos_payload = (
        b"\x01"
        b"\x01\x00"
        b"\x00"
        b"\x3F"
        b"\x00"
    )

    return (
        b"\xFF\xD8"
        + b"".join(
            app_segments
        )
        + segment(
            0xDB,
            dqt_payload,
        )
        + segment(
            0xC0,
            sof_payload,
        )
        + segment(
            0xDA,
            sos_payload,
        )
        + scan_data
        + b"\xFF\xD9"
    )


class TestImageComparison(
    unittest.TestCase
):

    def compare_bytes(
        self,
        original: bytes,
        copy: bytes,
    ):

        temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            temp.cleanup
        )

        root = Path(
            temp.name
        )

        original_path = (
            root
            / "original.jpg"
        )

        copy_path = (
            root
            / "copy.jpg"
        )

        original_path.write_bytes(
            original
        )

        copy_path.write_bytes(
            copy
        )

        return compare_images(
            original_path,
            copy_path,
        )

    def test_identical_images(
        self,
    ):

        jpeg = create_jpeg()

        report = self.compare_bytes(
            jpeg,
            jpeg,
        )

        self.assertTrue(
            report.identical_files
        )

        self.assertEqual(
            report.changes,
            (),
        )

        self.assertEqual(
            report.recompression.level,
            RECOMPRESSION_NONE,
        )

    def test_detects_removed_exif_and_gps(
        self,
    ):

        original = create_jpeg(
            app_segments=(
                gps_segment(),
            )
        )

        copy = create_jpeg()

        report = self.compare_bytes(
            original,
            copy,
        )

        self.assertTrue(
            report.has_change(
                "exif_removed"
            )
        )

        self.assertTrue(
            report.has_change(
                "gps_removed"
            )
        )

        self.assertEqual(
            report.recompression.level,
            RECOMPRESSION_NONE,
        )

    def test_detects_removed_camera_model(
        self,
    ):

        original = create_jpeg(
            app_segments=(
                model_segment(),
            )
        )

        copy = create_jpeg()

        report = self.compare_bytes(
            original,
            copy,
        )

        self.assertEqual(
            report.original.camera_model,
            "SM-S938B",
        )

        self.assertIsNone(
            report.copy.camera_model
        )

        self.assertTrue(
            report.has_change(
                "camera_model_removed"
            )
        )

    def test_detects_removed_xmp(
        self,
    ):

        original = create_jpeg(
            app_segments=(
                xmp_segment(),
            )
        )

        copy = create_jpeg()

        report = self.compare_bytes(
            original,
            copy,
        )

        self.assertTrue(
            report.has_change(
                "xmp_removed"
            )
        )

    def test_detects_resolution_change(
        self,
    ):

        report = self.compare_bytes(
            create_jpeg(
                width=32,
                height=16,
            ),
            create_jpeg(
                width=16,
                height=8,
                scan_data=(
                    b"\x44\x55\x66"
                ),
            ),
        )

        self.assertTrue(
            report.has_change(
                "resolution_changed"
            )
        )

    def test_marks_recompression_likely(
        self,
    ):

        report = self.compare_bytes(
            create_jpeg(
                quantization_value=5,
                scan_data=(
                    b"\x11\x22\x33"
                ),
            ),
            create_jpeg(
                width=16,
                height=8,
                quantization_value=12,
                scan_data=(
                    b"\x44\x55\x66"
                ),
            ),
        )

        self.assertEqual(
            report.recompression.level,
            RECOMPRESSION_LIKELY,
        )

        self.assertTrue(
            report.has_change(
                "quantization_changed"
            )
        )

        self.assertTrue(
            report.has_change(
                "compressed_data_changed"
            )
        )

    def test_marks_changed_scan_as_possible(
        self,
    ):

        report = self.compare_bytes(
            create_jpeg(
                scan_data=(
                    b"\x11\x22\x33"
                ),
            ),
            create_jpeg(
                scan_data=(
                    b"\x44\x55\x66"
                ),
            ),
        )

        self.assertEqual(
            report.recompression.level,
            RECOMPRESSION_POSSIBLE,
        )

    def test_metadata_only_change_has_no_recompression_evidence(
        self,
    ):

        report = self.compare_bytes(
            create_jpeg(
                app_segments=(
                    xmp_segment(),
                )
            ),
            create_jpeg(),
        )

        self.assertEqual(
            report.original.scan_data_sha256,
            report.copy.scan_data_sha256,
        )

        self.assertEqual(
            report.recompression.level,
            RECOMPRESSION_NONE,
        )

    def test_formats_comparison_report(
        self,
    ):

        report = self.compare_bytes(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            ),
            create_jpeg(),
        )

        text = (
            format_comparison_report(
                report
            )
        )

        self.assertIn(
            "METADATA COMPARISON",
            text,
        )

        self.assertIn(
            "ORIGINAL",
            text,
        )

        self.assertIn(
            "COPY",
            text,
        )

        self.assertIn(
            "EXIF metadata removed",
            text,
        )

        self.assertIn(
            "GPS metadata removed",
            text,
        )

        self.assertIn(
            "Recompression assessment:",
            text,
        )


if __name__ == "__main__":
    unittest.main()
