from __future__ import annotations

import csv
import io
import tempfile
import unittest
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path

from photometa.analysis.batch import (
    analyze_directory,
)
from photometa.cli import (
    main,
)
from photometa.exporters.csv_export import (
    CSV_COLUMNS,
    write_batch_csv,
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


class TestCsvExport(
    unittest.TestCase
):

    def make_directory(
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

    def read_rows(
        self,
        path: Path,
    ) -> list[
        dict[str, str]
    ]:

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            return list(
                csv.DictReader(
                    file
                )
            )

    def test_csv_writes_expected_columns(
        self,
    ):

        root = (
            self.make_directory()
        )

        (
            root
            / "photo.jpg"
        ).write_bytes(
            create_jpeg()
        )

        report = (
            analyze_directory(
                root
            )
        )

        output = (
            root.parent
            / (
                root.name
                + "-result.csv"
            )
        )

        self.addCleanup(
            lambda: (
                output.unlink()
                if output.exists()
                else None
            )
        )

        write_batch_csv(
            report,
            output,
        )

        with output.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = (
                csv.DictReader(
                    file
                )
            )

            self.assertEqual(
                tuple(
                    reader.fieldnames
                    or ()
                ),
                CSV_COLUMNS,
            )

        self.assertNotIn(
            "latitude",
            CSV_COLUMNS,
        )

        self.assertNotIn(
            "longitude",
            CSV_COLUMNS,
        )

    def test_csv_writes_jpeg_metadata_and_privacy(
        self,
    ):

        root = (
            self.make_directory()
        )

        (
            root
            / "photo.jpg"
        ).write_bytes(
            create_jpeg(
                app_segments=(
                    gps_segment(),
                )
            )
        )

        report = (
            analyze_directory(
                root
            )
        )

        output = (
            root / "result.csv"
        )

        write_batch_csv(
            report,
            output,
        )

        rows = self.read_rows(
            output
        )

        self.assertEqual(
            len(rows),
            1,
        )

        row = rows[0]

        self.assertEqual(
            row["schema_version"],
            "1.0",
        )

        self.assertEqual(
            row["format"],
            "JPEG",
        )

        self.assertEqual(
            row["analyzed"],
            "YES",
        )

        self.assertEqual(
            row["metadata_exif"],
            "YES",
        )

        self.assertEqual(
            row["metadata_gps"],
            "YES",
        )

        self.assertEqual(
            row["gps_detected"],
            "YES",
        )

        self.assertEqual(
            row["privacy_points"],
            "40",
        )

    def test_csv_includes_png_and_unsupported(
        self,
    ):

        root = (
            self.make_directory()
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

        output = (
            root / "result.csv"
        )

        write_batch_csv(
            report,
            output,
        )

        rows = self.read_rows(
            output
        )

        formats = {
            row["format"]
            for row in rows
        }

        self.assertEqual(
            formats,
            {
                "PNG",
                "UNSUPPORTED",
            },
        )

    def test_csv_uses_relative_paths(
        self,
    ):

        root = (
            self.make_directory()
        )

        (
            root
            / "photo.jpg"
        ).write_bytes(
            create_jpeg()
        )

        report = (
            analyze_directory(
                root
            )
        )

        output = (
            root / "result.csv"
        )

        write_batch_csv(
            report,
            output,
        )

        row = self.read_rows(
            output
        )[0]

        self.assertEqual(
            row["path"],
            "photo.jpg",
        )

    def test_cli_exports_directory_csv(
        self,
    ):

        root = (
            self.make_directory()
        )

        (
            root
            / "photo.jpg"
        ).write_bytes(
            create_jpeg()
        )

        output = (
            root / "result.csv"
        )

        stdout = (
            io.StringIO()
        )

        with redirect_stdout(
            stdout
        ):

            result = main(
                [
                    "scan",
                    str(root),
                    "--csv",
                    str(output),
                ]
            )

        self.assertEqual(
            result,
            0,
        )

        self.assertTrue(
            output.exists()
        )

        self.assertIn(
            "CSV EXPORT",
            stdout.getvalue(),
        )

        self.assertEqual(
            len(
                self.read_rows(
                    output
                )
            ),
            1,
        )

    def test_recursive_csv(
        self,
    ):

        root = (
            self.make_directory()
        )

        nested = (
            root / "nested"
        )

        nested.mkdir()

        (
            nested
            / "photo.jpg"
        ).write_bytes(
            create_jpeg()
        )

        output = (
            root / "result.csv"
        )

        result = main(
            [
                "scan",
                str(root),
                "--recursive",
                "--csv",
                str(output),
            ]
        )

        self.assertEqual(
            result,
            0,
        )

        rows = self.read_rows(
            output
        )

        self.assertEqual(
            len(rows),
            1,
        )

        self.assertEqual(
            rows[0]["path"],
            (
                "nested/"
                "photo.jpg"
            ),
        )

    def test_existing_csv_is_excluded_from_scan(
        self,
    ):

        root = (
            self.make_directory()
        )

        (
            root
            / "photo.jpg"
        ).write_bytes(
            create_jpeg()
        )

        output = (
            root / "result.csv"
        )

        output.write_text(
            "old data"
        )

        result = main(
            [
                "scan",
                str(root),
                "--csv",
                str(output),
            ]
        )

        self.assertEqual(
            result,
            0,
        )

        rows = self.read_rows(
            output
        )

        self.assertEqual(
            len(rows),
            1,
        )

        self.assertEqual(
            rows[0]["path"],
            "photo.jpg",
        )

    def test_csv_rejects_single_file(
        self,
    ):

        root = (
            self.make_directory()
        )

        photo = (
            root / "photo.jpg"
        )

        photo.write_bytes(
            create_jpeg()
        )

        stderr = (
            io.StringIO()
        )

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "scan",
                    str(photo),
                    "--csv",
                    str(
                        root
                        / "result.csv"
                    ),
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "--csv requires "
                "a directory"
            ),
            stderr.getvalue(),
        )

    def test_csv_rejects_json_combination(
        self,
    ):

        root = (
            self.make_directory()
        )

        stderr = (
            io.StringIO()
        )

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "scan",
                    str(root),
                    "--json",
                    "--csv",
                    str(
                        root
                        / "result.csv"
                    ),
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "--json cannot be "
                "combined with --csv"
            ),
            stderr.getvalue(),
        )

    def test_csv_rejects_segments_combination(
        self,
    ):

        root = (
            self.make_directory()
        )

        stderr = (
            io.StringIO()
        )

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "scan",
                    str(root),
                    "--segments",
                    "--csv",
                    str(
                        root
                        / "result.csv"
                    ),
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "--csv cannot be "
                "combined with --segments"
            ),
            stderr.getvalue(),
        )

    def test_csv_rejects_sensitive_option(
        self,
    ):

        root = (
            self.make_directory()
        )

        stderr = (
            io.StringIO()
        )

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "scan",
                    str(root),
                    "--include-sensitive",
                    "--csv",
                    str(
                        root
                        / "result.csv"
                    ),
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "--include-sensitive "
                "is not available "
                "with --csv"
            ),
            stderr.getvalue(),
        )


if __name__ == "__main__":

    unittest.main()
