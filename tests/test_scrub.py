import tempfile
import unittest
from pathlib import Path

from photometa.parsers.icc import (
    ICC_IDENTIFIER,
)
from photometa.parsers.xmp import (
    XMP_IDENTIFIER,
)
from photometa.sanitization.scrub import (
    ScrubError,
    _rewrite_jpeg_bytes,
    default_output_path,
    scrub_jpeg,
)
from tests.test_gps_ifd import (
    build_gps_tiff,
)


def segment(
    marker: int,
    payload: bytes,
) -> bytes:

    length = (
        len(payload) + 2
    )

    return (
        b"\xFF"
        + bytes(
            (marker,)
        )
        + length.to_bytes(
            2,
            "big",
        )
        + payload
    )


def create_jpeg(
    application_segments: tuple[
        bytes,
        ...
    ] = (),
    scan_data: bytes = (
        b"\x11\x22\x33"
    ),
) -> bytes:

    #
    # Structurally sufficient SOF0:
    #
    # precision = 8
    # height = 16
    # width = 32
    # components = 1
    #
    sof_payload = (
        b"\x08"
        b"\x00\x10"
        b"\x00\x20"
        b"\x01"
        b"\x01\x11\x00"
    )

    #
    # One-component SOS.
    #
    sos_payload = (
        b"\x01"
        b"\x01\x00"
        b"\x00"
        b"\x3F"
        b"\x00"
    )

    return (
        b"\xFF\xD8"
        + b"".join(
            application_segments
        )
        + segment(
            0xC0,
            sof_payload,
        )
        + segment(
            0xDA,
            sos_payload,
        )
        + scan_data
        + b"\xFF\xD9"
    )


def gps_exif_segment() -> bytes:

    payload = (
        b"Exif\x00\x00"
        + build_gps_tiff()
    )

    return segment(
        0xE1,
        payload,
    )


class TestScrub(
    unittest.TestCase
):

    def test_default_output_path(
        self,
    ):

        self.assertEqual(
            default_output_path(
                Path(
                    "/tmp/photo.jpg"
                )
            ),
            Path(
                "/tmp/photo_clean.jpg"
            ),
        )

    def test_removes_exif_and_gps(
        self,
    ):

        jpeg = create_jpeg(
            (
                gps_exif_segment(),
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            input_path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            input_path.write_bytes(
                jpeg
            )

            original_bytes = (
                input_path.read_bytes()
            )

            report = scrub_jpeg(
                input_path
            )

            sanitized = (
                report.output_path
                .read_bytes()
            )

            self.assertTrue(
                report.original_gps
            )

            self.assertFalse(
                report.sanitized_gps
            )

            self.assertNotIn(
                b"Exif\x00\x00",
                sanitized,
            )

            self.assertEqual(
                input_path.read_bytes(),
                original_bytes,
            )

            self.assertTrue(
                report.original_unchanged
            )

            self.assertTrue(
                report.dimensions_preserved
            )

            self.assertTrue(
                report.image_data_preserved
            )

    def test_removes_xmp(
        self,
    ):

        xmp = segment(
            0xE1,
            (
                XMP_IDENTIFIER
                + b"<x:xmpmeta/>"
            ),
        )

        jpeg = create_jpeg(
            (xmp,)
        )

        result = _rewrite_jpeg_bytes(
            jpeg
        )

        self.assertNotIn(
            XMP_IDENTIFIER,
            result.data,
        )

        self.assertEqual(
            len(
                result.removed_segments
            ),
            1,
        )

        self.assertEqual(
            result.removed_segments[
                0
            ].reason,
            "XMP metadata",
        )

    def test_removes_app13_and_comment(
        self,
    ):

        app13 = segment(
            0xED,
            (
                b"Photoshop 3.0\x00"
                b"metadata"
            ),
        )

        comment = segment(
            0xFE,
            b"private comment",
        )

        jpeg = create_jpeg(
            (
                app13,
                comment,
            )
        )

        result = _rewrite_jpeg_bytes(
            jpeg
        )

        self.assertNotIn(
            b"private comment",
            result.data,
        )

        self.assertNotIn(
            b"Photoshop 3.0",
            result.data,
        )

        self.assertEqual(
            len(
                result.removed_segments
            ),
            2,
        )

    def test_preserves_icc_profile(
        self,
    ):

        icc = segment(
            0xE2,
            (
                ICC_IDENTIFIER
                + b"\x01\x01"
                + b"fake-profile"
            ),
        )

        jpeg = create_jpeg(
            (icc,)
        )

        result = _rewrite_jpeg_bytes(
            jpeg
        )

        self.assertIn(
            ICC_IDENTIFIER,
            result.data,
        )

        self.assertEqual(
            result.removed_segments,
            (),
        )

    def test_preserves_jfif_and_adobe_app14(
        self,
    ):

        jfif = segment(
            0xE0,
            (
                b"JFIF\x00"
                b"\x01\x02"
            ),
        )

        adobe = segment(
            0xEE,
            (
                b"Adobe"
                b"\x00\x64"
            ),
        )

        jpeg = create_jpeg(
            (
                jfif,
                adobe,
            )
        )

        result = _rewrite_jpeg_bytes(
            jpeg
        )

        self.assertIn(
            b"JFIF\x00",
            result.data,
        )

        self.assertIn(
            b"Adobe",
            result.data,
        )

        self.assertEqual(
            result.removed_segments,
            (),
        )

    def test_preserves_entropy_data(
        self,
    ):

        scan_data = (
            b"\x11"
            b"\x22"
            b"\xFF\x00"
            b"\x33"
            b"\xFF\xD0"
            b"\x44"
        )

        jpeg = create_jpeg(
            (
                segment(
                    0xE1,
                    b"Exif\x00\x00fake",
                ),
            ),
            scan_data=scan_data,
        )

        result = _rewrite_jpeg_bytes(
            jpeg
        )

        verification = (
            _rewrite_jpeg_bytes(
                result.data
            )
        )

        self.assertEqual(
            result.scan_data_sha256,
            verification.scan_data_sha256,
        )

        self.assertIn(
            scan_data,
            result.data,
        )

    def test_removes_metadata_between_scans(
        self,
    ):

        sos_payload = (
            b"\x01"
            b"\x01\x00"
            b"\x00"
            b"\x3F"
            b"\x00"
        )

        sof_payload = (
            b"\x08"
            b"\x00\x10"
            b"\x00\x20"
            b"\x01"
            b"\x01\x11\x00"
        )

        jpeg = (
            b"\xFF\xD8"
            + segment(
                0xC0,
                sof_payload,
            )
            + segment(
                0xDA,
                sos_payload,
            )
            + b"\x11\x22"
            + segment(
                0xE1,
                (
                    b"Exif\x00\x00"
                    b"late-metadata"
                ),
            )
            + segment(
                0xDA,
                sos_payload,
            )
            + b"\x33\x44"
            + b"\xFF\xD9"
        )

        result = _rewrite_jpeg_bytes(
            jpeg
        )

        self.assertNotIn(
            b"late-metadata",
            result.data,
        )

        verification = (
            _rewrite_jpeg_bytes(
                result.data
            )
        )

        self.assertEqual(
            result.scan_data_sha256,
            verification.scan_data_sha256,
        )

    def test_removes_bytes_after_eoi(
        self,
    ):

        jpeg = (
            create_jpeg()
            + b"PRIVATE-TRAILING-DATA"
        )

        result = _rewrite_jpeg_bytes(
            jpeg
        )

        self.assertGreater(
            result.trailing_bytes_removed,
            0,
        )

        self.assertTrue(
            result.data.endswith(
                b"\xFF\xD9"
            )
        )

        self.assertNotIn(
            b"PRIVATE-TRAILING-DATA",
            result.data,
        )

    def test_refuses_to_overwrite_existing_output(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            input_path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            output_path = (
                Path(temp_dir)
                / "clean.jpg"
            )

            input_path.write_bytes(
                create_jpeg()
            )

            output_path.write_bytes(
                b"existing"
            )

            with self.assertRaises(
                ScrubError
            ):

                scrub_jpeg(
                    input_path,
                    output_path,
                )

    def test_refuses_in_place_scrub(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            input_path = (
                Path(temp_dir)
                / "photo.jpg"
            )

            input_path.write_bytes(
                create_jpeg()
            )

            with self.assertRaises(
                ScrubError
            ):

                scrub_jpeg(
                    input_path,
                    input_path,
                )

    def test_rejects_non_jpeg(
        self,
    ):

        with tempfile.TemporaryDirectory() as temp_dir:

            input_path = (
                Path(temp_dir)
                / "fake.jpg"
            )

            input_path.write_bytes(
                b"not-a-jpeg"
            )

            with self.assertRaises(
                ScrubError
            ):

                scrub_jpeg(
                    input_path
                )


if __name__ == "__main__":
    unittest.main()
