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
from tests.test_ifd0 import (
    create_tiff_data,
)
from tests.test_scrub import (
    create_jpeg,
    gps_exif_segment,
    segment,
)


def privacy_exif_segment() -> bytes:

    return segment(
        0xE1,
        (
            b"Exif\x00\x00"
            + create_tiff_data()
        ),
    )


class TestSelectiveScrubCli(
    unittest.TestCase
):

    def test_scrub_gps_mode(
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

            stdout = io.StringIO()

            with redirect_stdout(
                stdout
            ):

                result = main(
                    [
                        "scrub",
                        str(path),
                        "--gps",
                    ]
                )

            report = stdout.getvalue()

            self.assertEqual(
                result,
                0,
            )

            self.assertIn(
                "Mode:",
                report,
            )

            self.assertIn(
                "GPS",
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

    def test_scrub_privacy_mode(
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
                        privacy_exif_segment(),
                    )
                )
            )

            stdout = io.StringIO()

            with redirect_stdout(
                stdout
            ):

                result = main(
                    [
                        "scrub",
                        str(path),
                        "--privacy",
                    ]
                )

            report = stdout.getvalue()

            self.assertEqual(
                result,
                0,
            )

            self.assertIn(
                "PRIVACY",
                report,
            )

            self.assertIn(
                "Privacy findings: 0",
                report,
            )

    def test_gps_and_privacy_are_mutually_exclusive(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            path.write_bytes(
                create_jpeg()
            )

            stderr = io.StringIO()

            with (
                redirect_stderr(
                    stderr
                ),
                self.assertRaises(
                    SystemExit
                ),
            ):

                main(
                    [
                        "scrub",
                        str(path),
                        "--gps",
                        "--privacy",
                    ]
                )

            self.assertIn(
                "not allowed with argument",
                stderr.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
