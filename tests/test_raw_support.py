from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import (
    redirect_stderr,
)
from importlib.util import (
    find_spec,
)
from pathlib import Path
from unittest.mock import patch

from photometa.analysis.batch import (
    FORMAT_RAW,
    FORMAT_UNSUPPORTED,
    detect_batch_file_format,
)
from photometa.cli import (
    main,
)
from photometa.formats.raw_backend import (
    RawImageSnapshot,
    get_raw_backend_info,
    is_raw_candidate_path,
    probe_raw_file,
)
from photometa.presentation.raw_scan import (
    format_raw_scan_report,
)


RAWPY_AVAILABLE = (
    find_spec(
        "rawpy"
    )
    is not None
)


class TestRawSupport(
    unittest.TestCase
):

    def make_root(
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

    def test_common_raw_extensions_are_candidates(
        self,
    ):

        for name in (
            "photo.NEF",
            "photo.cr2",
            "photo.CR3",
            "photo.arw",
            "photo.raf",
            "photo.rw2",
            "photo.dng",
            "photo.orf",
            "photo.pef",
        ):

            with self.subTest(
                name=name
            ):

                self.assertTrue(
                    is_raw_candidate_path(
                        name
                    )
                )

    def test_normal_images_are_not_raw_candidates(
        self,
    ):

        for name in (
            "photo.jpg",
            "photo.png",
            "photo.webp",
            "photo.tiff",
            "photo.heic",
        ):

            with self.subTest(
                name=name
            ):

                self.assertFalse(
                    is_raw_candidate_path(
                        name
                    )
                )

    @unittest.skipUnless(
        RAWPY_AVAILABLE,
        "rawpy is not installed",
    )
    def test_backend_version_info(
        self,
    ):

        info = (
            get_raw_backend_info()
        )

        self.assertNotEqual(
            info.rawpy_version,
            "unknown",
        )

        self.assertTrue(
            info.libraw_version
        )

    @unittest.skipUnless(
        RAWPY_AVAILABLE,
        "rawpy is not installed",
    )
    def test_probe_rejects_fake_raw(
        self,
    ):

        root = self.make_root()

        path = (
            root / "fake.nef"
        )

        path.write_bytes(
            b"not a real raw file"
        )

        self.assertFalse(
            probe_raw_file(
                path
            )
        )

    @patch(
        "photometa.analysis.batch."
        "probe_raw_file",
        return_value=True,
    )
    @patch(
        "photometa.analysis.batch."
        "raw_backend_available",
        return_value=True,
    )
    def test_batch_classifies_libraw_validated_raw(
        self,
        mock_available,
        mock_probe,
    ):

        root = self.make_root()

        path = (
            root / "photo.dng"
        )

        #
        # DNG is TIFF-derived.
        #
        # This ensures RAW probing happens
        # before generic TIFF classification.
        #
        path.write_bytes(
            b"II\x2A\x00"
            + b"\x00" * 20
        )

        self.assertEqual(
            detect_batch_file_format(
                path
            ),
            FORMAT_RAW,
        )

        mock_available.assert_called_once()
        mock_probe.assert_called_once()

    @patch(
        "photometa.analysis.batch."
        "raw_backend_available",
        return_value=False,
    )
    def test_dng_is_not_mislabeled_tiff_without_backend(
        self,
        mock_available,
    ):

        root = self.make_root()

        path = (
            root / "photo.dng"
        )

        path.write_bytes(
            b"II\x2A\x00"
            + b"\x00" * 20
        )

        self.assertEqual(
            detect_batch_file_format(
                path
            ),
            FORMAT_UNSUPPORTED,
        )

        mock_available.assert_called_once()

    def test_single_file_json_is_deferred(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.nef"
        )

        path.write_bytes(
            b"candidate only"
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
                    str(path),
                    "--json",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            (
                "Single-file JSON export "
                "is not yet implemented "
                "for RAW"
            ),
            stderr.getvalue(),
        )

    def test_raw_formatter_marks_basic_support(
        self,
    ):

        snapshot = RawImageSnapshot(
            path=Path(
                "/tmp/photo.nef"
            ),
            format="RAW",
            variant="NEF",
            backend=(
                "rawpy / LibRaw"
            ),
            support_level=(
                "OPTIONAL / BASIC"
            ),
            rawpy_version="0.27.1",
            libraw_version="0.21.4",
            size_bytes=1000,
            sha256="a" * 64,
            raw_width=100,
            raw_height=80,
            visible_width=96,
            visible_height=76,
            top_margin=2,
            left_margin=2,
            crop_width=0,
            crop_height=0,
            pixel_aspect=1.0,
            orientation_code=0,
            raw_type="Flat",
            num_colors=3,
            color_description="RGBG",
            white_level=16383,
            black_level_per_channel=(
                512,
                512,
                512,
                512,
            ),
            camera_white_level_per_channel=None,
            camera_white_balance=None,
            daylight_white_balance=None,
            iso_speed=100.0,
            shutter_speed=0.01,
            aperture=2.8,
            focal_length=35.0,
            timestamp=None,
            shot_order=0,
            artist=None,
            lens_make=None,
            lens_model=None,
            lens_min_focal=None,
            lens_max_focal=None,
            enabled_features=(),
            warnings=(),
        )

        text = (
            format_raw_scan_report(
                snapshot
            )
        )

        self.assertIn(
            "Format:        RAW",
            text,
        )

        self.assertIn(
            "RAW variant:   NEF",
            text,
        )

        self.assertIn(
            "Backend:       rawpy / LibRaw",
            text,
        )

        self.assertIn(
            (
                "Support:       "
                "OPTIONAL / BASIC"
            ),
            text,
        )


if __name__ == "__main__":

    unittest.main()
