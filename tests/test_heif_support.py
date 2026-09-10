from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from importlib.util import (
    find_spec,
)
from pathlib import Path

from PIL import Image

from photometa.analysis.batch import (
    FORMAT_HEIF,
    analyze_directory,
    detect_batch_file_format,
)
from photometa.cli import (
    main,
)
from photometa.exporters.json_export import (
    build_batch_scan_json_document,
)
from photometa.formats.heif_backend import (
    FORMAT_HEIC,
    FORMAT_HEIF as SINGLE_FORMAT_HEIF,
    detect_heif_container,
    inspect_heif_image,
)


PILLOW_HEIF_AVAILABLE = (
    find_spec(
        "pillow_heif"
    )
    is not None
)


def make_ftyp(
    major: bytes,
    *compatible: bytes,
) -> bytes:

    payload = (
        major
        + b"\x00\x00\x00\x00"
        + b"".join(
            compatible
        )
    )

    size = (
        8
        + len(
            payload
        )
    )

    return (
        size.to_bytes(
            4,
            "big",
        )
        + b"ftyp"
        + payload
    )


class TestHeifSupport(
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

    def create_heif(
        self,
        path: Path,
    ) -> None:

        if not PILLOW_HEIF_AVAILABLE:

            self.skipTest(
                "pillow-heif is not installed"
            )

        import pillow_heif

        image = Image.new(
            "RGB",
            (
                16,
                12,
            ),
            (
                30,
                60,
                90,
            ),
        )

        heif_file = (
            pillow_heif.from_pillow(
                image
            )
        )

        try:

            heif_file.save(
                path,
                quality=90,
            )

        except Exception as exc:

            self.skipTest(
                (
                    "HEIF encoder is "
                    f"unavailable: {exc}"
                )
            )

    def test_detects_heic_brand_without_backend(
        self,
    ):

        root = self.make_root()

        path = (
            root / "sample.bin"
        )

        path.write_bytes(
            make_ftyp(
                b"heic",
                b"mif1",
                b"heic",
            )
        )

        result = (
            detect_heif_container(
                path
            )
        )

        self.assertIsNotNone(
            result
        )

        assert result is not None

        self.assertEqual(
            result.format,
            FORMAT_HEIC,
        )

    def test_does_not_misclassify_avif(
        self,
    ):

        root = self.make_root()

        path = (
            root / "sample.avif"
        )

        path.write_bytes(
            make_ftyp(
                b"avif",
                b"mif1",
            )
        )

        self.assertIsNone(
            detect_heif_container(
                path
            )
        )

    def test_batch_detects_heif_signature(
        self,
    ):

        root = self.make_root()

        path = (
            root / "sample.heic"
        )

        path.write_bytes(
            make_ftyp(
                b"heic",
                b"mif1",
            )
        )

        self.assertEqual(
            detect_batch_file_format(
                path
            ),
            FORMAT_HEIF,
        )

    def test_batch_counts_heif(
        self,
    ):

        root = self.make_root()

        (
            root
            / "sample.heic"
        ).write_bytes(
            make_ftyp(
                b"heic",
                b"mif1",
            )
        )

        report = (
            analyze_directory(
                root
            )
        )

        self.assertEqual(
            report.heif_count,
            1,
        )

        self.assertEqual(
            report.unsupported_count,
            0,
        )

    def test_batch_json_counts_heif(
        self,
    ):

        root = self.make_root()

        (
            root
            / "sample.heif"
        ).write_bytes(
            make_ftyp(
                b"mif1",
            )
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

        self.assertEqual(
            document[
                "summary"
            ][
                "formats"
            ][
                "heif"
            ],
            1,
        )

    @unittest.skipUnless(
        PILLOW_HEIF_AVAILABLE,
        (
            "pillow-heif optional "
            "dependency not installed"
        ),
    )
    def test_real_heif_basic_scan(
        self,
    ):

        root = self.make_root()

        path = (
            root / "sample.heic"
        )

        self.create_heif(
            path
        )

        result = (
            inspect_heif_image(
                path
            )
        )

        self.assertIn(
            result.format,
            (
                FORMAT_HEIC,
                SINGLE_FORMAT_HEIF,
            ),
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
            "pillow-heif / libheif",
        )

    @unittest.skipUnless(
        PILLOW_HEIF_AVAILABLE,
        (
            "pillow-heif optional "
            "dependency not installed"
        ),
    )
    def test_cli_scans_real_heif(
        self,
    ):

        root = self.make_root()

        path = (
            root / "sample.heic"
        )

        self.create_heif(
            path
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
            (
                "Backend:       "
                "pillow-heif / libheif"
            ),
            text,
        )

        self.assertIn(
            (
                "Support:       "
                "OPTIONAL / BASIC"
            ),
            text,
        )

    def test_single_file_json_is_deferred(
        self,
    ):

        root = self.make_root()

        path = (
            root / "sample.heic"
        )

        path.write_bytes(
            make_ftyp(
                b"heic",
                b"mif1",
            )
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
                "for HEIC/HEIF"
            ),
            stderr.getvalue(),
        )


if __name__ == "__main__":

    unittest.main()
