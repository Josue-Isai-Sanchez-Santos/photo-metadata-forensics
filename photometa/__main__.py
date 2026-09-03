from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from photometa.analysis.anomalies import (
    AnomalyAnalysisError,
    analyze_anomalies,
)
from photometa.presentation.anomalies import (
    format_anomaly_report,
)

from photometa.analysis.comparison import (
    ComparisonError,
    compare_images,
)
from photometa.presentation.comparison import (
    format_comparison_report,
)

from photometa.hashing import (
    HashingError,
    calculate_hash,
    calculate_hashes,
)
from photometa.sanitization.scrub import (
    ScrubError,
    scrub_jpeg,
)
from photometa.sanitization.selective import (
    SCRUB_MODE_GPS,
    SCRUB_MODE_PRIVACY,
    SelectiveScrubReport,
    scrub_jpeg_selective,
)


SCRUB_MODE_ALL = "all"


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



    anomalies_parser = (
        commands.add_parser(
            "anomalies",
            help=(
                "Analyze metadata and JPEG "
                "structure for anomalies."
            ),
        )
    )

    anomalies_parser.add_argument(
        "path",
        type=Path,
        help=(
            "JPEG file to analyze."
        ),
    )

    compare_parser = commands.add_parser(
        "compare",
        help=(
            "Compare metadata and JPEG "
            "characteristics between "
            "two images."
        ),
    )

    compare_parser.add_argument(
        "original",
        type=Path,
        help=(
            "Original/reference JPEG."
        ),
    )

    compare_parser.add_argument(
        "copy",
        type=Path,
        help=(
            "Copy/derived JPEG to compare."
        ),
    )

    scrub_parser = commands.add_parser(
        "scrub",
        help=(
            "Create a sanitized JPEG copy."
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

    scrub_modes = (
        scrub_parser
        .add_mutually_exclusive_group()
    )

    scrub_modes.add_argument(
        "--all",
        dest="scrub_mode",
        action="store_const",
        const=SCRUB_MODE_ALL,
        help=(
            "Remove all removable metadata. "
            "This is the default."
        ),
    )

    scrub_modes.add_argument(
        "--gps",
        dest="scrub_mode",
        action="store_const",
        const=SCRUB_MODE_GPS,
        help=(
            "Remove GPS metadata while "
            "preserving other metadata."
        ),
    )

    scrub_modes.add_argument(
        "--privacy",
        dest="scrub_mode",
        action="store_const",
        const=SCRUB_MODE_PRIVACY,
        help=(
            "Remove supported privacy-sensitive "
            "metadata while preserving "
            "non-sensitive metadata."
        ),
    )

    scrub_parser.set_defaults(
        scrub_mode=SCRUB_MODE_ALL
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

    if args.command == "anomalies":

        try:

            report = analyze_anomalies(
                args.path
            )

            print(
                format_anomaly_report(
                    report
                )
            )

            return 0

        except AnomalyAnalysisError as exc:

            print(
                f"error: {exc}",
                file=sys.stderr,
            )

            return 1

    if args.command == "compare":

        try:

            report = compare_images(
                args.original,
                args.copy,
            )

            print(
                format_comparison_report(
                    report
                )
            )

            return 0

        except ComparisonError as exc:

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
                mode=args.scrub_mode,
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
    mode: str = SCRUB_MODE_ALL,
) -> int:

    if mode == SCRUB_MODE_ALL:

        report = scrub_jpeg(
            path,
            output,
        )

        _print_all_scrub_report(
            report
        )

        return 0

    report = scrub_jpeg_selective(
        path,
        output,
        mode=mode,
    )

    _print_selective_scrub_report(
        report
    )

    return 0


def _print_all_scrub_report(
    report: object,
) -> None:

    print("SCRUB")
    print("-" * 60)
    print("Mode:       ALL")

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


def _print_selective_scrub_report(
    report: SelectiveScrubReport,
) -> None:

    print("SCRUB")
    print("-" * 60)

    print(
        "Mode:      ",
        report.mode.upper(),
    )

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

    print(
        "Privacy findings:",
        report.privacy_findings_before,
    )

    print()

    print("Sanitized:")

    print(
        "GPS:",
        _yes_no(
            report.sanitized_gps
        ),
    )

    print(
        "Privacy findings:",
        report.privacy_findings_after,
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
        report.removed_segment_count,
    )

    print(
        "Modified segments:",
        report.modified_segment_count,
    )

    print(
        "File bytes removed:",
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
