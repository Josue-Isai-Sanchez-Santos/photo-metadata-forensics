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


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
