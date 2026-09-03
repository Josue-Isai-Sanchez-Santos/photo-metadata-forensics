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
from tests.test_comparison import (
    create_jpeg,
    gps_segment,
)


class TestCompareCli(
    unittest.TestCase
):

    def test_compare_command(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            root = Path(
                temp_dir
            )

            original = (
                root
                / "original.jpg"
            )

            copy = (
                root
                / "copy.jpg"
            )

            original.write_bytes(
                create_jpeg(
                    app_segments=(
                        gps_segment(),
                    )
                )
            )

            copy.write_bytes(
                create_jpeg()
            )

            stdout = io.StringIO()

            with redirect_stdout(
                stdout
            ):

                result = main(
                    [
                        "compare",
                        str(original),
                        str(copy),
                    ]
                )

            text = stdout.getvalue()

            self.assertEqual(
                result,
                0,
            )

            self.assertIn(
                "METADATA COMPARISON",
                text,
            )

            self.assertIn(
                "EXIF metadata removed",
                text,
            )

            self.assertIn(
                "GPS metadata removed",
                text,
            )

    def test_compare_missing_file(
        self,
    ):

        stderr = io.StringIO()

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "compare",
                    "missing-original.jpg",
                    "missing-copy.jpg",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            "does not exist",
            stderr.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
