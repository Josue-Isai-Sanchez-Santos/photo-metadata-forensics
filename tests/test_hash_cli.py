import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from photometa.__main__ import (
    main,
)


class TestHashCli(unittest.TestCase):

    def test_hash_command_defaults_to_sha256(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.bin"
            )

            path.write_bytes(
                b"abc"
            )

            output = io.StringIO()

            with redirect_stdout(
                output
            ):

                result = main(
                    [
                        "hash",
                        str(path),
                    ]
                )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "SHA256",
            output.getvalue(),
        )

        self.assertIn(
            (
                "ba7816bf8f01cfea"
                "414140de5dae2223"
                "b00361a396177a9c"
                "b410ff61f20015ad"
            ),
            output.getvalue(),
        )

    def test_hash_command_supports_md5(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.bin"
            )

            path.write_bytes(
                b"abc"
            )

            output = io.StringIO()

            with redirect_stdout(
                output
            ):

                result = main(
                    [
                        "hash",
                        str(path),
                        "--algorithm",
                        "md5",
                    ]
                )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "MD5",
            output.getvalue(),
        )

        self.assertIn(
            "900150983cd24fb0d6963f7d28e17f72",
            output.getvalue(),
        )

    def test_hash_command_supports_all(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = (
                Path(temp_dir)
                / "sample.bin"
            )

            path.write_bytes(
                b"abc"
            )

            output = io.StringIO()

            with redirect_stdout(
                output
            ):

                result = main(
                    [
                        "hash",
                        str(path),
                        "--all",
                    ]
                )

        report = output.getvalue()

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "SHA256",
            report,
        )

        self.assertIn(
            "SHA1",
            report,
        )

        self.assertIn(
            "MD5",
            report,
        )


if __name__ == "__main__":
    unittest.main()
