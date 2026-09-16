from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path

from PIL import (
    Image,
    features,
)

from photometa.analysis.batch import (
    FORMAT_JPEG,
    FORMAT_TIFF,
    FORMAT_WEBP,
    analyze_directory,
    detect_batch_file_format,
)
from photometa.cli import (
    main,
)
from photometa.exporters.json_export import (
    build_batch_scan_json_document,
)
from photometa.formats.pillow_backend import (
    detect_scan_format,
    inspect_additional_image,
)
from tests.test_comparison import (
    create_jpeg,
)


class TestAdditionalFormats(
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

    def create_image(
        self,
        path: Path,
        format_name: str,
    ) -> None:

        image = Image.new(
            "RGB",
            (
                16,
                12,
            ),
            (
                10,
                20,
                30,
            ),
        )

        image.save(
            path,
            format=format_name,
        )

    def test_png_basic_scan(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.png"
        )

        self.create_image(
            path,
            "PNG",
        )

        result = (
            inspect_additional_image(
                path
            )
        )

        self.assertEqual(
            result.format,
            "PNG",
        )

        self.assertEqual(
            (
                result.width,
                result.height,
            ),
            (
                16,
                12,
            ),
        )

        self.assertEqual(
            result.backend,
            "Pillow",
        )

    def test_tiff_basic_scan(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.tiff"
        )

        self.create_image(
            path,
            "TIFF",
        )

        result = (
            inspect_additional_image(
                path
            )
        )

        self.assertEqual(
            result.format,
            "TIFF",
        )

        self.assertEqual(
            result.resolution,
            "16x12",
        )

        #
        # A plain TIFF contains normal TIFF
        # IFD tags, but that alone must not
        # be reported as an EXIF extension.
        #
        self.assertEqual(
            result.exif_status,
            "NO",
        )

        self.assertEqual(
            result.exif_gps_status,
            "NO",
        )

    @unittest.skipUnless(
        features.check(
            "webp"
        ),
        (
            "Pillow WebP support "
            "not available"
        ),
    )
    def test_webp_basic_scan(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.webp"
        )

        self.create_image(
            path,
            "WEBP",
        )

        result = (
            inspect_additional_image(
                path
            )
        )

        self.assertEqual(
            result.format,
            "WEBP",
        )

    def test_cli_scans_png(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.png"
        )

        self.create_image(
            path,
            "PNG",
        )

        stdout = io.StringIO()

        with redirect_stdout(
            stdout
        ):

            result = main(
                [
                    "scan",
                    str(path),
                ]
            )

        self.assertEqual(
            result,
            0,
        )

        text = (
            stdout.getvalue()
        )

        self.assertIn(
            "Format:        PNG",
            text,
        )

        self.assertIn(
            "Support:       BASIC",
            text,
        )

    def test_json_for_png_is_explicitly_deferred(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.png"
        )

        self.create_image(
            path,
            "PNG",
        )

        stderr = io.StringIO()

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
                "for PNG"
            ),
            stderr.getvalue(),
        )

    def test_batch_detects_webp_and_tiff(
        self,
    ):

        root = self.make_root()

        tiff = (
            root / "photo.tiff"
        )

        self.create_image(
            tiff,
            "TIFF",
        )

        self.assertEqual(
            detect_batch_file_format(
                tiff
            ),
            FORMAT_TIFF,
        )

        if features.check(
            "webp"
        ):

            webp = (
                root / "photo.webp"
            )

            self.create_image(
                webp,
                "WEBP",
            )

            self.assertEqual(
                detect_batch_file_format(
                    webp
                ),
                FORMAT_WEBP,
            )

    def test_batch_json_counts_new_formats(
        self,
    ):

        root = self.make_root()

        self.create_image(
            root / "photo.tiff",
            "TIFF",
        )

        if features.check(
            "webp"
        ):

            self.create_image(
                root / "photo.webp",
                "WEBP",
            )

        report = (
            analyze_directory(
                root
            )
        )

        document = (
            build_batch_scan_json_document(
                report
            )
        )

        formats = (
            document[
                "summary"
            ][
                "formats"
            ]
        )

        self.assertEqual(
            formats["tiff"],
            1,
        )

        self.assertIn(
            "webp",
            formats,
        )

    def test_jpeg_remains_jpeg(
        self,
    ):

        root = self.make_root()

        path = (
            root / "photo.jpg"
        )

        path.write_bytes(
            create_jpeg()
        )

        self.assertEqual(
            detect_scan_format(
                path
            ),
            FORMAT_JPEG,
        )


if __name__ == "__main__":

    unittest.main()
