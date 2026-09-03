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
)


class TestAnomaliesCli(
    unittest.TestCase
):

    def test_anomalies_command(
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

            stdout = io.StringIO()

            with redirect_stdout(
                stdout
            ):

                result = main(
                    [
                        "anomalies",
                        str(path),
                    ]
                )

            text = stdout.getvalue()

            self.assertEqual(
                result,
                0,
            )

            self.assertIn(
                "ANOMALIES",
                text,
            )

            self.assertIn(
                (
                    "No anomalies detected"
                ),
                text,
            )

            self.assertIn(
                (
                    "This does not prove "
                    "image manipulation."
                ),
                text,
            )

    def test_anomalies_missing_file(
        self,
    ):

        stderr = io.StringIO()

        with redirect_stderr(
            stderr
        ):

            result = main(
                [
                    "anomalies",
                    "missing.jpg",
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
