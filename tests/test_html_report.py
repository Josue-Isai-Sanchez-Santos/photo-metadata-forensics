from __future__ import annotations

import io
import os
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
from photometa.exporters.html_report import (
    HtmlReportError,
    build_html_report,
    write_html_report,
)
from tests.test_comparison import (
    create_jpeg,
    gps_segment,
)


class TestHtmlReport(
    unittest.TestCase
):

    def make_file(
        self,
        *,
        gps: bool = False,
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
            / "photo.jpg"
        )

        app_segments = (
            (gps_segment(),)
            if gps
            else ()
        )

        path.write_bytes(
            create_jpeg(
                app_segments=(
                    app_segments
                )
            )
        )

        return (
            temp,
            path,
        )

    def test_html_contains_required_sections(
        self,
    ):

        _, path = self.make_file()

        text = build_html_report(
            path
        )

        for heading in (
            "File Information",
            "Metadata Presence",
            "Hashes",
            "Capture",
            "EXIF — IFD0",
            "EXIF — ExifIFD",
            "Location",
            "Privacy",
            "Anomalies",
            (
                "Interpretation of "
                "Special Values"
            ),
        ):

            self.assertIn(
                heading,
                text,
            )

    def test_html_is_standalone_document(
        self,
    ):

        _, path = self.make_file()

        text = build_html_report(
            path
        )

        self.assertTrue(
            text.startswith(
                "<!doctype html>"
            )
        )

        self.assertIn(
            "<meta charset=\"utf-8\">",
            text,
        )

        self.assertNotIn(
            "<script src=",
            text,
        )

        self.assertNotIn(
            "<link rel=\"stylesheet\"",
            text,
        )

    def test_hashes_are_included(
        self,
    ):

        _, path = self.make_file()

        text = build_html_report(
            path
        )

        self.assertIn(
            "SHA-256",
            text,
        )

        self.assertIn(
            "SHA-1",
            text,
        )

        self.assertIn(
            "MD5",
            text,
        )

    def test_gps_hidden_by_default(
        self,
    ):

        _, path = self.make_file(
            gps=True
        )

        text = build_html_report(
            path
        )

        self.assertIn(
            (
                "Exact coordinates and "
                "raw GPS values are hidden"
            ),
            text,
        )

        self.assertNotIn(
            "<th>Latitude</th>",
            text,
        )

        self.assertNotIn(
            "<th>Longitude</th>",
            text,
        )

    def test_sensitive_gps_can_be_included(
        self,
    ):

        _, path = self.make_file(
            gps=True
        )

        text = build_html_report(
            path,
            include_sensitive=True,
        )

        self.assertIn(
            "<th>Latitude</th>",
            text,
        )

        self.assertIn(
            "<th>Longitude</th>",
            text,
        )

        self.assertIn(
            "Raw GPS EXIF",
            text,
        )

    def test_writes_custom_output(
        self,
    ):

        temp, path = self.make_file()

        output = (
            Path(temp.name)
            / "custom.html"
        )

        written = write_html_report(
            path,
            output,
        )

        self.assertEqual(
            written,
            output.resolve(),
        )

        self.assertTrue(
            output.exists()
        )

    def test_refuses_existing_output(
        self,
    ):

        temp, path = self.make_file()

        output = (
            Path(temp.name)
            / "report.html"
        )

        output.write_text(
            "existing"
        )

        with self.assertRaises(
            HtmlReportError
        ):

            write_html_report(
                path,
                output,
            )

    def test_force_replaces_existing_output(
        self,
    ):

        temp, path = self.make_file()

        output = (
            Path(temp.name)
            / "report.html"
        )

        output.write_text(
            "existing"
        )

        write_html_report(
            path,
            output,
            force=True,
        )

        self.assertTrue(
            output.read_text(
                encoding="utf-8"
            ).startswith(
                "<!doctype html>"
            )
        )

    def test_cli_default_creates_report_html(
        self,
    ):

        temp, path = self.make_file()

        old_cwd = Path.cwd()

        stdout = io.StringIO()
        stderr = io.StringIO()

        try:

            os.chdir(
                temp.name
            )

            with (
                redirect_stdout(
                    stdout
                ),
                redirect_stderr(
                    stderr
                ),
            ):

                result = main(
                    [
                        "report",
                        str(path),
                    ]
                )

            output = (
                Path(temp.name)
                / "report.html"
            )

            self.assertEqual(
                result,
                0,
            )

            self.assertTrue(
                output.exists()
            )

            self.assertIn(
                "HTML REPORT",
                stdout.getvalue(),
            )

            self.assertEqual(
                stderr.getvalue(),
                "",
            )

        finally:

            os.chdir(
                old_cwd
            )


if __name__ == "__main__":

    unittest.main()
