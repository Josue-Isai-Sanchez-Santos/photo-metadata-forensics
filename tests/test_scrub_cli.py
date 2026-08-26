import io
import tempfile
import unittest
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path

from photometa.__main__ import (
    main,
)
from tests.test_scrub import (
    create_jpeg,
    gps_exif_segment,
)


class TestScrubCli(
    unittest.TestCase
):

    def test_scrub_uses_default_output(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            path.write_bytes(
                create_jpeg(
                    (
                        gps_exif_segment(),
                    )
                )
            )

            output = io.StringIO()

            with redirect_stdout(
                output
            ):

                result = main(
                    [
                        "scrub",
                        str(path),
                    ]
                )

            clean_path = (
                Path(temp_dir)
                / "photo_clean.jpg"
            )

            self.assertEqual(
                result,
                0,
            )

            self.assertTrue(
                clean_path.exists()
            )

            report = (
                output.getvalue()
            )

            self.assertIn(
                "Original:",
                report,
            )

            self.assertIn(
                "Sanitized:",
                report,
            )

            self.assertIn(
                "GPS: YES",
                report,
            )

            self.assertIn(
                "GPS: NO",
                report,
            )

            self.assertIn(
                "Image data preserved: YES",
                report,
            )

    def test_scrub_supports_custom_output(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output_path = (
                Path(temp_dir)
                / "limpia.jpg"
            )

            path.write_bytes(
                create_jpeg()
            )

            output = io.StringIO()

            with redirect_stdout(
                output
            ):

                result = main(
                    [
                        "scrub",
                        str(path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(
                result,
                0,
            )

            self.assertTrue(
                output_path.exists()
            )

    def test_scrub_refuses_existing_output(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output_path = (
                Path(temp_dir)
                / "limpia.jpg"
            )

            path.write_bytes(
                create_jpeg()
            )

            output_path.write_bytes(
                b"do-not-overwrite"
            )

            error = io.StringIO()

            with redirect_stderr(
                error
            ):

                result = main(
                    [
                        "scrub",
                        str(path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(
                result,
                1,
            )

            self.assertIn(
                "already exists",
                error.getvalue(),
            )

            self.assertEqual(
                output_path.read_bytes(),
                b"do-not-overwrite",
            )


if __name__ == "__main__":
    unittest.main()
