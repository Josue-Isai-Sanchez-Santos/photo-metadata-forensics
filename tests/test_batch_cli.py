from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path

from photometa.cli import (
    main,
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


class TestBatchCli(
    unittest.TestCase
):

    def make_directory(
        self,
    ) -> tuple[
        tempfile.TemporaryDirectory,
        Path,
    ]:

        temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            temp.cleanup
        )

        root = Path(
            temp.name
        )

        return (
            temp,
            root,
        )

    def test_scan_directory(
        self,
    ):

        _, root = (
            self.make_directory()
        )

        (
            root
            / "photo.jpg"
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

        stdout = io.StringIO()

        with redirect_stdout(
            stdout
        ):

            result = main(
                [
                    "scan",
                    str(root),
                ]
            )

        text = stdout.getvalue()

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "BATCH SCAN",
            text,
        )

        self.assertIn(
            "1 JPEG",
            text,
        )

        self.assertIn(
            "1 PNG",
            text,
        )

        self.assertIn(
            "1 unsupported",
            text,
        )

    def test_privacy_directory(
        self,
    ):

        _, root = (
            self.make_directory()
        )

        (
            root
            / "high.jpg"
        ).write_bytes(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                    xmp_segment(),
                )
            )
        )

        stdout = io.StringIO()

        with redirect_stdout(
            stdout
        ):

            result = main(
                [
                    "privacy",
                    str(root),
                ]
            )

        text = stdout.getvalue()

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "BATCH PRIVACY ANALYSIS",
            text,
        )

        self.assertIn(
            "GPS metadata detected:  1",
            text,
        )

        self.assertIn(
            "HIGH:                   1",
            text,
        )

    def test_recursive_option(
        self,
    ):

        _, root = (
            self.make_directory()
        )

        nested = (
            root
            / "nested"
        )

        nested.mkdir()

        (
            nested
            / "photo.jpg"
        ).write_bytes(
            create_jpeg()
        )

        stdout = io.StringIO()

        with redirect_stdout(
            stdout
        ):

            result = main(
                [
                    "scan",
                    str(root),
                    "--recursive",
                ]
            )

        text = stdout.getvalue()

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "Recursive: YES",
            text,
        )

        self.assertIn(
            "1 JPEG",
            text,
        )

    def test_segments_rejected_for_directory(
        self,
    ):

        _, root = (
            self.make_directory()
        )

        (
            root
            / "photo.jpg"
        ).write_bytes(
            create_jpeg()
        )

        stderr = io.StringIO()

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "scan",
                    str(root),
                    "--segments",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "--segments is only "
                "available"
            ),
            stderr.getvalue(),
        )


if __name__ == "__main__":

    unittest.main()
