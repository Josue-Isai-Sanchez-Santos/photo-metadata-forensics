from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from photometa.hashing import (
    HashingError,
    calculate_hash,
    calculate_hashes,
)
from photometa.sanitization.scrub import (
    ScrubError,
    scrub_jpeg,
)


ALGORITHM_LABELS = {
    "sha256": "SHA256",
    "sha1": "SHA1",
    "md5": "MD5",
}


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="photometa",
        description=(
            "Image metadata and forensic "
            "analysis toolkit."
        ),
    )

    commands = parser.add_subparsers(
        dest="command",
    )

    hash_parser = commands.add_parser(
        "hash",
        help=(
            "Calculate a forensic file hash."
        ),
    )

    hash_parser.add_argument(
        "path",
        type=Path,
        help="File to hash.",
    )

    hash_group = (
        hash_parser
        .add_mutually_exclusive_group()
    )

    hash_group.add_argument(
        "-a",
        "--algorithm",
        choices=(
            "sha256",
            "sha1",
            "md5",
        ),
        default="sha256",
        help=(
            "Hash algorithm. "
            "Default: sha256."
        ),
    )

    hash_group.add_argument(
        "--all",
        action="store_true",
        help=(
            "Calculate SHA-256, SHA-1 "
            "and MD5."
        ),
    )

    scrub_parser = commands.add_parser(
        "scrub",
        help=(
            "Create a privacy-sanitized "
            "JPEG copy."
        ),
    )

    scrub_parser.add_argument(
        "path",
        type=Path,
        help=(
            "JPEG file to sanitize."
        ),
    )

    scrub_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Output file. "
            "Default: <name>_clean.jpg"
        ),
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:

    parser = build_parser()

    args = parser.parse_args(
        argv
    )

    if args.command == "hash":

        try:

            return run_hash_command(
                path=args.path,
                algorithm=args.algorithm,
                all_hashes=args.all,
            )

        except HashingError as exc:

            print(
                f"error: {exc}",
                file=sys.stderr,
            )

            return 1

    if args.command == "scrub":

        try:

            return run_scrub_command(
                path=args.path,
                output=args.output,
            )

        except ScrubError as exc:

            print(
                f"error: {exc}",
                file=sys.stderr,
            )

            return 1

    parser.print_help()

    return 0


def run_hash_command(
    path: Path,
    algorithm: str = "sha256",
    all_hashes: bool = False,
) -> int:

    print("HASH")
    print("-" * 60)
    print(
        f"File:       {path}"
    )

    if all_hashes:

        hashes = calculate_hashes(
            path,
            (
                "sha256",
                "sha1",
                "md5",
            ),
        )

        for name in (
            "sha256",
            "sha1",
            "md5",
        ):

            print(
                f"{ALGORITHM_LABELS[name]:<10}: "
                f"{hashes[name]}"
            )

    else:

        digest = calculate_hash(
            path,
            algorithm,
        )

        print(
            f"{ALGORITHM_LABELS[algorithm]:<10}: "
            f"{digest}"
        )

    return 0


def run_scrub_command(
    path: Path,
    output: Path | None = None,
) -> int:

    report = scrub_jpeg(
        path,
        output,
    )

    print("SCRUB")
    print("-" * 60)

    print(
        f"Original:   "
        f"{report.input_path}"
    )

    print(
        f"Sanitized:  "
        f"{report.output_path}"
    )

    print()

    print("Original:")
    print(
        "GPS:",
        _yes_no(
            report.original_gps
        ),
    )

    print()

    print("Sanitized:")
    print(
        "GPS:",
        _yes_no(
            report.sanitized_gps
        ),
    )

    print()

    print(
        "JPEG structure valid:",
        "YES",
    )

    print(
        "Dimensions preserved:",
        _yes_no(
            report.dimensions_preserved
        ),
    )

    print(
        "Image data preserved:",
        _yes_no(
            report.image_data_preserved
        ),
    )

    print(
        "Original unchanged:",
        _yes_no(
            report.original_unchanged
        ),
    )

    print()

    print(
        "Removed segments:",
        len(
            report.removed_segments
        ),
    )

    print(
        "Removed bytes:",
        report.removed_bytes,
    )

    if (
        report.trailing_bytes_removed
        > 0
    ):

        print(
            "Trailing bytes removed:",
            report.trailing_bytes_removed,
        )

    return 0


def _yes_no(
    value: bool,
) -> str:

    return (
        "YES"
        if value
        else "NO"
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
