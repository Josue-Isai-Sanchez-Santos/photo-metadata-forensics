import unittest

from photometa.parsers.tags import (
    get_tiff_tag_name,
)


class TestTiffTags(unittest.TestCase):

    def test_known_tag(self):

        self.assertEqual(
            get_tiff_tag_name(
                0x010F
            ),
            "Make",
        )

    def test_known_pointer_tag(self):

        self.assertEqual(
            get_tiff_tag_name(
                0x8769
            ),
            "ExifIFDPointer",
        )

    def test_unknown_tag(self):

        self.assertEqual(
            get_tiff_tag_name(
                0xDEAD
            ),
            "UnknownTag_DEAD",
        )


if __name__ == "__main__":
    unittest.main()
