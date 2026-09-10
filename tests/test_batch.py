from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from photometa.analysis.batch import (
    FORMAT_JPEG,
    FORMAT_PNG,
    FORMAT_UNSUPPORTED,
    analyze_directory,
    detect_batch_file_format,
)
from tests.test_comparison import (
    create_jpeg,
    gps_segment,
)
from tests.test_selective_scrub import (
    xmp_segment,
)


PNG_SAMPLE = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\x0D"
    b"IHDR"
    b"\x00\x00\x00\x01"
    b"\x00\x00\x00\x01"
)


class TestBatchAnalysis(
    unittest.TestCase
):

    def make_temp_dir(
        self,
    ) -> Path:

        temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            temp.cleanup
        )

        return Path(
            temp.name
        )

    def test_detects_formats_by_signature(
        self,
    ):

        root = self.make_temp_dir()

        jpeg = root / "jpeg.bin"
        png = root / "png.bin"
        other = root / "other.jpg"

        jpeg.write_bytes(
            create_jpeg()
        )

        png.write_bytes(
            PNG_SAMPLE
        )

        other.write_bytes(
            b"not-an-image"
        )

        self.assertEqual(
            detect_batch_file_format(
                jpeg
            ),
            FORMAT_JPEG,
        )

        self.assertEqual(
            detect_batch_file_format(
                png
            ),
            FORMAT_PNG,
        )

        self.assertEqual(
            detect_batch_file_format(
                other
            ),
            FORMAT_UNSUPPORTED,
        )

    def test_counts_jpeg_png_and_unsupported(
        self,
    ):

        root = self.make_temp_dir()

        (
            root
            / "one.jpg"
        ).write_bytes(
            create_jpeg()
        )

        (
            root
            / "two.jpeg"
        ).write_bytes(
            create_jpeg()
        )

        (
            root
            / "image.png"
        ).write_bytes(
            PNG_SAMPLE
        )

        (
            root
            / "notes.txt"
        ).write_text(
            "hello"
        )

        report = (
            analyze_directory(
                root
            )
        )

        self.assertEqual(
            report.total_files,
            4,
        )

        self.assertEqual(
            report.jpeg_count,
            2,
        )

        self.assertEqual(
            report.png_count,
            1,
        )

        self.assertEqual(
            report.unsupported_count,
            1,
        )

    def test_non_recursive_ignores_nested_files(
        self,
    ):

        root = self.make_temp_dir()

        (
            root
            / "top.jpg"
        ).write_bytes(
            create_jpeg()
        )

        nested = (
            root
            / "nested"
        )

        nested.mkdir()

        (
            nested
            / "inside.jpg"
        ).write_bytes(
            create_jpeg()
        )

        report = (
            analyze_directory(
                root
            )
        )

        self.assertEqual(
            report.total_files,
            1,
        )

        self.assertEqual(
            report.jpeg_count,
            1,
        )

    def test_recursive_includes_nested_files(
        self,
    ):

        root = self.make_temp_dir()

        (
            root
            / "top.jpg"
        ).write_bytes(
            create_jpeg()
        )

        nested = (
            root
            / "nested"
        )

        nested.mkdir()

        (
            nested
            / "inside.jpg"
        ).write_bytes(
            create_jpeg()
        )

        report = (
            analyze_directory(
                root,
                recursive=True,
            )
        )

        self.assertEqual(
            report.total_files,
            2,
        )

        self.assertEqual(
            report.jpeg_count,
            2,
        )

    def test_detects_gps_and_high_exposure(
        self,
    ):

        root = self.make_temp_dir()

        high = (
            root
            / "high.jpg"
        )

        high.write_bytes(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                    xmp_segment(),
                )
            )
        )

        report = (
            analyze_directory(
                root
            )
        )

        self.assertEqual(
            report.gps_detected_count,
            1,
        )

        self.assertEqual(
            report.high_privacy_count,
            1,
        )

    def test_corrupt_jpeg_does_not_stop_batch(
        self,
    ):

        root = self.make_temp_dir()

        (
            root
            / "good.jpg"
        ).write_bytes(
            create_jpeg()
        )

        (
            root
            / "broken.jpg"
        ).write_bytes(
            b"\xFF\xD8broken"
        )

        report = (
            analyze_directory(
                root
            )
        )

        self.assertEqual(
            report.jpeg_count,
            2,
        )

        self.assertEqual(
            report.analyzed_jpeg_count,
            1,
        )

        self.assertEqual(
            report.failed_jpeg_count,
            1,
        )

    def test_empty_directory_is_valid(
        self,
    ):

        root = self.make_temp_dir()

        report = (
            analyze_directory(
                root
            )
        )

        self.assertEqual(
            report.total_files,
            0,
        )

        self.assertEqual(
            report.jpeg_count,
            0,
        )

        self.assertEqual(
            report.high_privacy_count,
            0,
        )


if __name__ == "__main__":

    unittest.main()
