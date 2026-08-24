import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from photometa.fileinfo import (
    FileInfoError,
    analyze_file,
    calculate_sha256,
    detect_file_format,
    format_file_size,
)
from photometa.presentation.fileinfo import (
    format_file_info_report,
)


def create_jpeg_bytes(
    width: int = 4000,
    height: int = 3000,
) -> bytes:
    """
    JPEG sintético suficiente para
    probar SOF0 y metadatos de archivo.
    """

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
        + b"\x03"
        + b"\x01\x11\x00"
        + b"\x02\x11\x01"
        + b"\x03\x11\x01"
    )

    sof_length = (
        len(sof_payload)
        + 2
    )

    return (
        b"\xFF\xD8"

        b"\xFF\xC0"
        + sof_length.to_bytes(
            2,
            "big",
        )
        + sof_payload

        + b"\xFF\xDA"
        + b"\x00\x02"
    )


class TestFileInfo(
    unittest.TestCase
):

    def test_analyzes_jpeg_file(
        self,
    ):

        data = create_jpeg_bytes()

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.jpg"
            )

            path.write_bytes(
                data
            )

            info = analyze_file(
                path
            )

        self.assertEqual(
            info.name,
            "sample.jpg",
        )

        self.assertEqual(
            info.extension,
            ".jpg",
        )

        self.assertEqual(
            info.file_type,
            "Image",
        )

        self.assertEqual(
            info.format,
            "JPEG",
        )

        self.assertEqual(
            info.mime_type,
            "image/jpeg",
        )

        self.assertEqual(
            info.width,
            4000,
        )

        self.assertEqual(
            info.height,
            3000,
        )

        self.assertEqual(
            info.resolution,
            "4000 × 3000",
        )

        self.assertEqual(
            info.size_bytes,
            len(data),
        )

    def test_detects_format_from_content(
        self,
    ):

        data = create_jpeg_bytes()

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "evidence.bin"
            )

            path.write_bytes(
                data
            )

            file_type, file_format, mime = (
                detect_file_format(
                    path
                )
            )

        self.assertEqual(
            file_type,
            "Image",
        )

        self.assertEqual(
            file_format,
            "JPEG",
        )

        self.assertEqual(
            mime,
            "image/jpeg",
        )

    def test_calculates_sha256(
        self,
    ):

        data = create_jpeg_bytes()

        expected = (
            hashlib.sha256(
                data
            ).hexdigest()
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.jpg"
            )

            path.write_bytes(
                data
            )

            actual = calculate_sha256(
                path
            )

        self.assertEqual(
            actual,
            expected,
        )

    def test_formats_file_size(
        self,
    ):

        self.assertEqual(
            format_file_size(
                6_420_000
            ),
            "6.42 MB",
        )

        self.assertEqual(
            format_file_size(
                950
            ),
            "950 B",
        )

    def test_rejects_unknown_format(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "fake.jpg"
            )

            path.write_bytes(
                b"This is not a JPEG."
            )

            with self.assertRaises(
                FileInfoError
            ):
                analyze_file(
                    path
                )

    def test_exposes_filesystem_timestamps(
        self,
    ):

        data = create_jpeg_bytes()

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.jpg"
            )

            path.write_bytes(
                data
            )

            info = analyze_file(
                path
            )

        self.assertIsNotNone(
            info.modified_at
        )

        self.assertIsNotNone(
            info.accessed_at
        )

        if os.name == "posix":
            self.assertIsNotNone(
                info.metadata_changed_at
            )

    def test_formats_file_report(
        self,
    ):

        data = create_jpeg_bytes()

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "IMG_20260811.jpg"
            )

            path.write_bytes(
                data
            )

            info = analyze_file(
                path
            )

            report = (
                format_file_info_report(
                    info
                )
            )

        self.assertIn(
            "FILE",
            report,
        )

        self.assertIn(
            "Name:              "
            "IMG_20260811.jpg",
            report,
        )

        self.assertIn(
            "Format:            JPEG",
            report,
        )

        self.assertIn(
            "Resolution:        "
            "4000 × 3000",
            report,
        )

        self.assertIn(
            "SHA256:",
            report,
        )

        self.assertIn(
            "filesystem timestamps "
            "are not EXIF capture timestamps",
            report,
        )


if __name__ == "__main__":
    unittest.main()
