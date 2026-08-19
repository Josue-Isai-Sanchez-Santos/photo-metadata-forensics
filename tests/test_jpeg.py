import tempfile
import unittest
from pathlib import Path

from photometa.parsers.jpeg import (
    JpegParserError,
    iter_jpeg_segments,
)


class TestJpegParser(unittest.TestCase):

    def test_detects_exif_app1(self):

        data = (
            b"\xFF\xD8"
            b"\xFF\xE1"
            b"\x00\x08"
            b"Exif\x00\x00"
            b"\xFF\xDA"
            b"\x00\x02"
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            path = Path(temp_dir) / "sample.jpg"
            path.write_bytes(data)

            segments = list(
                iter_jpeg_segments(path)
            )

        self.assertEqual(
            segments[0].name,
            "SOI",
        )

        self.assertEqual(
            segments[1].name,
            "APP1",
        )

        self.assertTrue(
            segments[1].is_exif
        )

        self.assertEqual(
            segments[2].name,
            "SOS",
        )

    def test_rejects_non_jpeg_file(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = Path(temp_dir) / "fake.jpg"

            path.write_bytes(
                b"This is not JPEG data"
            )

            with self.assertRaises(
                JpegParserError
            ):
                list(
                    iter_jpeg_segments(path)
                )


if __name__ == "__main__":
    unittest.main()
