from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import (
    patch,
)

from photometa.backends.exiftool_backend import (
    ExifToolSnapshot,
    ExifToolUnavailableError,
    inspect_with_exiftool,
)
from photometa.cli import (
    main,
)
from photometa.presentation.exiftool_scan import (
    format_exiftool_scan_report,
)


class TestExifToolBackend(
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

    def make_snapshot(
        self,
        path: Path,
    ) -> ExifToolSnapshot:

        return ExifToolSnapshot(
            path=path,
            backend="ExifTool",
            exiftool_version="13.00",
            file_type="JPEG",
            mime_type="image/jpeg",
            size_bytes=1000,
            sha256="a" * 64,
            width=4000,
            height=3000,
            tag_count=20,
            group_counts=(
                (
                    "ExifIFD",
                    8,
                ),
                (
                    "File",
                    5,
                ),
                (
                    "GPS",
                    4,
                ),
                (
                    "IFD0",
                    3,
                ),
            ),
            exif_status="YES",
            gps_status="YES",
            xmp_status="NO",
            iptc_status="NO",
            icc_status="NO",
            quicktime_status="NO",
            camera_make="Example",
            camera_model="Camera X",
            software=None,
            datetime_original=(
                "2025:01:01 12:00:00"
            ),
            lens_make=None,
            lens_model="Example Lens",
            orientation="1",
            warnings=(),
        )

    @patch(
        "photometa.backends."
        "exiftool_backend.shutil.which",
        return_value=None,
    )
    def test_missing_exiftool_is_reported(
        self,
        mock_which,
    ):

        root = self.make_root()

        path = (
            root / "photo.jpg"
        )

        path.write_bytes(
            b"test"
        )

        with self.assertRaises(
            ExifToolUnavailableError
        ):

            inspect_with_exiftool(
                path
            )

        mock_which.assert_called()

    @patch(
        "photometa.backends."
        "exiftool_backend.shutil.which",
        return_value="/usr/bin/exiftool",
    )
    @patch(
        "photometa.backends."
        "exiftool_backend.subprocess.run",
    )
    def test_parses_exiftool_json(
        self,
        mock_run,
        mock_which,
    ):

        root = self.make_root()

        path = (
            root / "photo.jpg"
        )

        path.write_bytes(
            b"example"
        )

        payload = [
            {
                "SourceFile": str(
                    path.resolve()
                ),
                "File:FileType": "JPEG",
                "File:MIMEType": (
                    "image/jpeg"
                ),
                "File:ImageWidth": 4000,
                "File:ImageHeight": 3000,
                "IFD0:Make": "Example",
                "IFD0:Model": "Camera X",
                "ExifIFD:DateTimeOriginal": (
                    "2025:01:01 12:00:00"
                ),
                "GPS:GPSLatitude": 19.1,
                "GPS:GPSLongitude": -96.1,
                "XMP-dc:Title": "Example",
            }
        ]

        mock_run.side_effect = [
            CompletedProcess(
                args=[],
                returncode=0,
                stdout="13.00\n",
                stderr="",
            ),
            CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    payload
                ),
                stderr="",
            ),
        ]

        snapshot = (
            inspect_with_exiftool(
                path
            )
        )

        self.assertEqual(
            snapshot.backend,
            "ExifTool",
        )

        self.assertEqual(
            snapshot.file_type,
            "JPEG",
        )

        self.assertEqual(
            snapshot.camera_model,
            "Camera X",
        )

        self.assertEqual(
            snapshot.exif_status,
            "YES",
        )

        self.assertEqual(
            snapshot.gps_status,
            "YES",
        )

        self.assertEqual(
            snapshot.xmp_status,
            "YES",
        )

        mock_which.assert_called()

    @patch(
        "photometa.backends."
        "exiftool_backend.shutil.which",
        return_value="/usr/bin/exiftool",
    )
    @patch(
        "photometa.backends."
        "exiftool_backend.subprocess.run",
    )
    def test_dng_prefers_raw_subifd_over_preview(
        self,
        mock_run,
        mock_which,
    ):

        root = self.make_root()

        path = (
            root / "photo.dng"
        )

        path.write_bytes(
            b"example dng"
        )

        payload = [
            {
                "SourceFile": str(
                    path.resolve()
                ),
                "File:FileType": "DNG",
                "File:MIMEType": (
                    "image/x-adobe-dng"
                ),

                #
                # Small embedded preview.
                #
                "IFD0:ImageWidth": 256,
                "IFD0:ImageHeight": 170,

                #
                # RAW image dimensions.
                #
                "SubIFD:ImageWidth": 3040,
                "SubIFD:ImageHeight": 2014,

                #
                # Metadata-declared crop.
                #
                "XMP-tiff:ImageWidth": 3008,
                "XMP-tiff:ImageHeight": 2000,
                "XMP-exif:ExifImageWidth": 3008,
                "XMP-exif:ExifImageHeight": 2000,
            }
        ]

        mock_run.side_effect = [
            CompletedProcess(
                args=[],
                returncode=0,
                stdout="13.50\n",
                stderr="",
            ),
            CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    payload
                ),
                stderr="",
            ),
        ]

        snapshot = (
            inspect_with_exiftool(
                path
            )
        )

        self.assertEqual(
            snapshot.width,
            3040,
        )

        self.assertEqual(
            snapshot.height,
            2014,
        )

        self.assertEqual(
            snapshot.resolution,
            "3040x2014",
        )

        mock_which.assert_called()

    def test_formatter_hides_exact_gps(
        self,
    ):

        root = self.make_root()

        snapshot = (
            self.make_snapshot(
                root / "photo.jpg"
            )
        )

        text = (
            format_exiftool_scan_report(
                snapshot
            )
        )

        self.assertIn(
            "GPS metadata detected: YES",
            text,
        )

        self.assertIn(
            "Exact GPS values are hidden",
            text,
        )

        self.assertNotIn(
            "19.123456",
            text,
        )

        self.assertNotIn(
            "-96.123456",
            text,
        )

    @patch(
        "photometa.cli."
        "inspect_with_exiftool",
    )
    def test_cli_uses_exiftool_backend(
        self,
        mock_inspect,
    ):

        root = self.make_root()

        path = (
            root / "photo.jpg"
        )

        path.write_bytes(
            b"example"
        )

        mock_inspect.return_value = (
            self.make_snapshot(
                path.resolve()
            )
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
                    str(path),
                    "--backend",
                    "exiftool",
                ]
            )

        self.assertEqual(
            result,
            0,
        )

        self.assertIn(
            "Backend:       ExifTool",
            stdout.getvalue(),
        )

        mock_inspect.assert_called_once()

    def test_exiftool_backend_rejects_directory(
        self,
    ):

        root = self.make_root()

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
                    "--backend",
                    "exiftool",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            "single file",
            stderr.getvalue(),
        )

    def test_exiftool_backend_rejects_json(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.heic"
        )

        path.write_bytes(
            b"example"
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
                    "--backend",
                    "exiftool",
                    "--json",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            "JSON export",
            stderr.getvalue(),
        )

    def test_exiftool_backend_rejects_segments(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.jpg"
        )

        path.write_bytes(
            b"example"
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
                    "--backend",
                    "exiftool",
                    "--segments",
                ]
            )

        self.assertEqual(
            result,
            1,
        )

        self.assertIn(
            "native JPEG parser",
            stderr.getvalue(),
        )

    def test_group_counts_are_rendered(
        self,
    ):

        root = self.make_root()

        snapshot = (
            self.make_snapshot(
                root / "photo.jpg"
            )
        )

        text = (
            format_exiftool_scan_report(
                snapshot
            )
        )

        self.assertIn(
            "EXIFTOOL GROUPS",
            text,
        )

        self.assertIn(
            "ExifIFD",
            text,
        )

        self.assertIn(
            "GPS",
            text,
        )


if __name__ == "__main__":

    unittest.main()
