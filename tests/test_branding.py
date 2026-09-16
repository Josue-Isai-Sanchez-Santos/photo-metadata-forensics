import unittest

from photometa.cli import (
    build_parser,
)
from photometa.presentation.branding import (
    MAIN_BANNER,
    MAIN_HELP_EPILOG,
    PRODUCT_NAME,
)


class TestCliBranding(
    unittest.TestCase
):

    def test_product_name_is_present(
        self,
    ):
        self.assertIn(
            "PHOTO METADATA FORENSICS",
            PRODUCT_NAME,
        )

    def test_banner_contains_product_name(
        self,
    ):
        self.assertIn(
            PRODUCT_NAME,
            MAIN_BANNER,
        )

    def test_help_contains_banner(
        self,
    ):
        help_text = (
            build_parser()
            .format_help()
        )

        self.assertIn(
            "PHOTO METADATA FORENSICS",
            help_text,
        )

        self.assertIn(
            "Image Metadata",
            help_text,
        )

    def test_help_contains_commands(
        self,
    ):
        help_text = (
            build_parser()
            .format_help()
        )

        for command in (
            "scan",
            "privacy",
            "gps",
            "report",
            "hash",
            "anomalies",
            "compare",
            "scrub",
        ):
            self.assertIn(
                command,
                help_text,
            )

    def test_help_contains_examples(
        self,
    ):
        help_text = (
            build_parser()
            .format_help()
        )

        examples = (
            "photometa scan foto.jpg",
            "photometa privacy foto.jpg",
            "photometa gps foto.jpg",
            (
                "photometa report foto.jpg "
                "--output report.html"
            ),
            (
                "photometa scrub foto.jpg "
                "--output foto_clean.jpg"
            ),
        )

        for example in examples:
            self.assertIn(
                example,
                help_text,
            )

    def test_epilog_has_quick_examples(
        self,
    ):
        self.assertIn(
            "Quick examples:",
            MAIN_HELP_EPILOG,
        )


if __name__ == "__main__":
    unittest.main()
