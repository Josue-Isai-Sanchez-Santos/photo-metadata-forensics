from __future__ import annotations

import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

import photometa.__main__ as package_main
import photometa.cli as cli

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


class TestCliEntrypoint(
    unittest.TestCase
):

    def test_pyproject_declares_console_script(
        self,
    ):

        pyproject = tomllib.loads(
            (
                PROJECT_ROOT
                / "pyproject.toml"
            ).read_text()
        )

        self.assertEqual(
            pyproject[
                "project"
            ][
                "scripts"
            ][
                "photometa"
            ],
            "photometa.cli:main",
        )

    def test_package_main_uses_cli_main(
        self,
    ):

        self.assertIs(
            package_main.main,
            cli.main,
        )

    def test_python_m_photometa_help(
        self,
    ):

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "photometa",
                "--help",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "anomalies",
            result.stdout,
        )

        self.assertIn(
            "compare",
            result.stdout,
        )

        self.assertIn(
            "scrub",
            result.stdout,
        )

    def test_python_m_photometa_cli_help(
        self,
    ):

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "photometa.cli",
                "--help",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "Image metadata and forensic",
            result.stdout,
        )

    def test_version_flag(
        self,
    ):

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "photometa",
                "--version",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
        )

        self.assertEqual(
            result.stdout.strip(),
            "photometa 0.1.0",
        )


if __name__ == "__main__":

    unittest.main()
