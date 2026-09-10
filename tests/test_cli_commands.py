from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import (
    redirect_stdout,
)
from pathlib import Path

from photometa.cli import (
    build_parser,
    main,
)
from tests.test_comparison import (
    create_jpeg,
    gps_segment,
)


class TestCliCommands(
    unittest.TestCase
):

    def write_jpeg(
        self,
        data: bytes,
        name: str = "photo.jpg",
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

        path = (
            Path(temp.name)
            / name
        )

        path.write_bytes(
            data
        )

        return (
            temp,
            path,
        )

    def run_cli(
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

    def test_help_lists_all_commands(
        self,
    ):

        text = (
            build_parser()
            .format_help()
        )

        for command in (
            "scan",
            "privacy",
            "gps",
            "hash",
            "compare",
            "scrub",
            "report",
            "anomalies",
        ):

            self.assertIn(
                command,
                text,
            )

    def test_scan_command(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg()
        )

        result, text = (
            self.run_cli(
                [
                    "scan",
                    str(path),
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "SCAN",
            text,
        )

        self.assertIn(
            "METADATA",
            text,
        )

        self.assertIn(
            "EXIF:",
            text,
        )

    def test_scan_segments(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg()
        )

        result, text = (
            self.run_cli(
                [
                    "scan",
                    str(path),
                    "--segments",
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "JPEG HEADER SEGMENTS",
            text,
        )

        self.assertIn(
            "SOF0",
            text,
        )

    def test_privacy_command(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        result, text = (
            self.run_cli(
                [
                    "privacy",
                    str(path),
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "PRIVACY ANALYSIS",
            text,
        )

        self.assertIn(
            "PRIVACY EXPOSURE SCORE",
            text,
        )

    def test_privacy_detailed_command(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        result, text = (
            self.run_cli(
                [
                    "privacy",
                    str(path),
                    "--detailed",
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "SCORING CONTRIBUTIONS",
            text,
        )

        self.assertIn(
            "Source:",
            text,
        )

    def test_gps_absent_is_not_error(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg()
        )

        result, text = (
            self.run_cli(
                [
                    "gps",
                    str(path),
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "GPS detected: NO",
            text,
        )

    def test_gps_raw_command(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        result, text = (
            self.run_cli(
                [
                    "gps",
                    str(path),
                    "--raw",
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "GPS detected: YES",
            text,
        )

        self.assertIn(
            "GPS RAW / FORENSIC",
            text,
        )

    def test_report_hides_coordinates_by_default(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        result, text = (
            self.run_cli(
                [
                    "report",
                    str(path),
                    "--text",
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "PHOTOMETA REPORT",
            text,
        )

        self.assertIn(
            (
                "Coordinates: hidden "
                "in default report"
            ),
            text,
        )

        self.assertNotIn(
            "Latitude:",
            text,
        )

    def test_report_can_include_sensitive_gps(
        self,
    ):

        _, path = self.write_jpeg(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        result, text = (
            self.run_cli(
                [
                    "report",
                    str(path),
                    "--text",
                    "--include-sensitive",
                ]
            )
        )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "Latitude:",
            text,
        )

        self.assertIn(
            "Longitude:",
            text,
        )


if __name__ == "__main__":

    unittest.main()
