from __future__ import annotations

import io
import json
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


PNG_SAMPLE = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\x0D"
    b"IHDR"
    b"\x00\x00\x00\x01"
    b"\x00\x00\x00\x01"
)


class TestJsonExport(
    unittest.TestCase
):

    def make_file(
        self,
        data: bytes,
        name: str = "photo.jpg",
    ) -> Path:

        temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            temp.cleanup
        )

        path = (
            Path(temp.name)
            / name
        )

        path.write_bytes(
            data
        )

        return path

    def run_stdout(
        self,
        argv: list[str],
    ) -> tuple[
        int,
        str,
    ]:

        stdout = io.StringIO()

        with redirect_stdout(
            stdout
        ):

            result = main(
                argv
            )

        return (
            result,
            stdout.getvalue(),
        )

    def test_scan_json_is_valid_json(
        self,
    ):

        path = self.make_file(
            create_jpeg()
        )

        result, text = (
            self.run_stdout(
                [
                    "scan",
                    str(path),
                    "--json",
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        document = json.loads(
            text
        )

        self.assertEqual(
            document[
                "schema_version"
            ],
            "1.0",
        )

        self.assertEqual(
            document["mode"],
            "single",
        )

    def test_scan_json_has_expected_groups(
        self,
    ):

        path = self.make_file(
            create_jpeg()
        )

        _, text = (
            self.run_stdout(
                [
                    "scan",
                    str(path),
                    "--json",
                ]
            )
        )

        document = json.loads(
            text
        )

        for key in (
            "file",
            "metadata",
            "device",
            "capture",
            "gps",
            "privacy",
            "warnings",
        ):

            self.assertIn(
                key,
                document,
            )

        self.assertEqual(
            document[
                "file"
            ][
                "format"
            ],
            "JPEG",
        )

    def test_scan_json_hides_gps_by_default(
        self,
    ):

        path = self.make_file(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        _, text = (
            self.run_stdout(
                [
                    "scan",
                    str(path),
                    "--json",
                ]
            )
        )

        gps = json.loads(
            text
        )["gps"]

        self.assertTrue(
            gps["detected"]
        )

        self.assertFalse(
            gps[
                "coordinates_included"
            ]
        )

        self.assertIsNone(
            gps["latitude"]
        )

        self.assertIsNone(
            gps["longitude"]
        )

    def test_scan_json_can_include_gps(
        self,
    ):

        path = self.make_file(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        _, text = (
            self.run_stdout(
                [
                    "scan",
                    str(path),
                    "--json",
                    "--include-sensitive",
                ]
            )
        )

        gps = json.loads(
            text
        )["gps"]

        self.assertTrue(
            gps["detected"]
        )

        self.assertTrue(
            gps[
                "coordinates_included"
            ]
        )

        self.assertIsNotNone(
            gps["latitude"]
        )

        self.assertIsNotNone(
            gps["longitude"]
        )

    def test_json_output_contains_no_human_header(
        self,
    ):

        path = self.make_file(
            create_jpeg()
        )

        _, text = (
            self.run_stdout(
                [
                    "scan",
                    str(path),
                    "--json",
                ]
            )
        )

        self.assertTrue(
            text.lstrip().startswith(
                "{"
            )
        )

        self.assertNotIn(
            "\nSCAN\n",
            text,
        )

        json.loads(
            text
        )

    def test_batch_scan_json(
        self,
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

        result, text = (
            self.run_stdout(
                [
                    "scan",
                    str(root),
                    "--json",
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        document = json.loads(
            text
        )

        self.assertEqual(
            document["mode"],
            "batch",
        )

        self.assertEqual(
            document[
                "summary"
            ][
                "total_files"
            ],
            3,
        )

        self.assertEqual(
            document[
                "summary"
            ][
                "formats"
            ][
                "jpeg"
            ],
            1,
        )

        self.assertEqual(
            document[
                "summary"
            ][
                "formats"
            ][
                "png"
            ],
            1,
        )

        self.assertEqual(
            document[
                "summary"
            ][
                "formats"
            ][
                "unsupported"
            ],
            1,
        )

    def test_json_and_segments_are_rejected(
        self,
    ):

        path = self.make_file(
            create_jpeg()
        )

        stderr = io.StringIO()

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "scan",
                    str(path),
                    "--json",
                    "--segments",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "--json cannot be combined "
                "with --segments"
            ),
            stderr.getvalue(),
        )

    def test_include_sensitive_requires_json(
        self,
    ):

        path = self.make_file(
            create_jpeg()
        )

        stderr = io.StringIO()

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "scan",
                    str(path),
                    "--include-sensitive",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "--include-sensitive "
                "requires --json"
            ),
            stderr.getvalue(),
        )


if __name__ == "__main__":

    unittest.main()
