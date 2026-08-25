import tempfile
import unittest
from pathlib import Path

from photometa.hashing import (
    HashingError,
    calculate_hash,
    calculate_hashes,
    calculate_md5,
    calculate_sha1,
    calculate_sha256,
    compare_files_by_hash,
    normalize_hash_algorithm,
)


class TestHashing(unittest.TestCase):

    def create_file(
        self,
        directory: str,
        name: str,
        data: bytes,
    ) -> Path:

        path = (
            Path(directory)
            / name
        )

        path.write_bytes(
            data
        )

        return path

    def test_calculates_sha256(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = self.create_file(
                temp_dir,
                "sample.bin",
                b"abc",
            )

            digest = calculate_sha256(
                path
            )

        self.assertEqual(
            digest,
            (
                "ba7816bf8f01cfea"
                "414140de5dae2223"
                "b00361a396177a9c"
                "b410ff61f20015ad"
            ),
        )

    def test_calculates_sha1(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = self.create_file(
                temp_dir,
                "sample.bin",
                b"abc",
            )

            digest = calculate_sha1(
                path
            )

        self.assertEqual(
            digest,
            (
                "a9993e364706816a"
                "ba3e25717850c26c"
                "9cd0d89d"
            ),
        )

    def test_calculates_md5(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = self.create_file(
                temp_dir,
                "sample.bin",
                b"abc",
            )

            digest = calculate_md5(
                path
            )

        self.assertEqual(
            digest,
            "900150983cd24fb0d6963f7d28e17f72",
        )

    def test_calculates_multiple_hashes(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            path = self.create_file(
                temp_dir,
                "sample.bin",
                b"abc",
            )

            hashes = calculate_hashes(
                path,
                (
                    "sha256",
                    "sha1",
                    "md5",
                ),
            )

        self.assertEqual(
            set(hashes),
            {
                "sha256",
                "sha1",
                "md5",
            },
        )

        self.assertEqual(
            len(
                hashes["sha256"]
            ),
            64,
        )

        self.assertEqual(
            len(
                hashes["sha1"]
            ),
            40,
        )

        self.assertEqual(
            len(
                hashes["md5"]
            ),
            32,
        )

    def test_normalizes_algorithm_names(
        self,
    ):

        self.assertEqual(
            normalize_hash_algorithm(
                "SHA-256"
            ),
            "sha256",
        )

        self.assertEqual(
            normalize_hash_algorithm(
                "SHA-1"
            ),
            "sha1",
        )

        self.assertEqual(
            normalize_hash_algorithm(
                "MD5"
            ),
            "md5",
        )

    def test_rejects_unknown_algorithm(
        self,
    ):

        with self.assertRaises(
            HashingError
        ):
            normalize_hash_algorithm(
                "sha512"
            )

    def test_equal_files_have_same_hash(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            first = self.create_file(
                temp_dir,
                "first.bin",
                b"same content",
            )

            second = self.create_file(
                temp_dir,
                "second.bin",
                b"same content",
            )

            result = compare_files_by_hash(
                first,
                second,
            )

        self.assertTrue(
            result
        )

    def test_different_files_have_different_hash(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            first = self.create_file(
                temp_dir,
                "first.bin",
                b"original",
            )

            second = self.create_file(
                temp_dir,
                "second.bin",
                b"modified",
            )

            result = compare_files_by_hash(
                first,
                second,
            )

        self.assertFalse(
            result
        )

    def test_rejects_missing_file(
        self,
    ):

        with self.assertRaises(
            HashingError
        ):
            calculate_hash(
                "/path/that/does/not/exist.jpg"
            )


if __name__ == "__main__":
    unittest.main()
