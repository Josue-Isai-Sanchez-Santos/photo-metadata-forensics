from __future__ import annotations

import argparse
import sys
from importlib.metadata import (
    PackageNotFoundError,
    version,
)
from pathlib import Path
from typing import Sequence

from photometa.analysis.anomalies import (
    AnomalyAnalysisError,
    analyze_anomalies,
)
from photometa.presentation.anomalies import (
    format_anomaly_report,
)

from photometa.analysis.batch import (
    BatchAnalysisError,
    analyze_directory,
)
from photometa.presentation.batch import (
    format_batch_privacy_report,
    format_batch_scan_report,
)

from photometa.analysis.comparison import (
    PRESENCE_NO,
    PRESENCE_UNKNOWN,
    ComparisonError,
    compare_images,
    inspect_image_for_comparison,
)
from photometa.presentation.comparison import (
    format_comparison_report,
)

from photometa.analysis.privacy import (
    analyze_privacy,
)
from photometa.analysis.privacy_score import (
    calculate_privacy_exposure_score,
)
from photometa.analysis.report import (
    FullReportError,
    build_full_report,
)
from photometa.extractors.gps_ifd import (
    GpsIfdExtractorError,
    build_location_summary,
    extract_gps_ifd_from_jpeg,
)
from photometa.parsers.iptc import (
    IptcParserError,
)
from photometa.parsers.jpeg import (
    JpegParserError,
    iter_jpeg_segments,
)
from photometa.parsers.xmp import (
    XmpParserError,
)
from photometa.presentation.gps import (
    format_gps_raw_report,
    format_location_report,
)
from photometa.presentation.privacy import (
    format_privacy_detailed_report,
    format_privacy_report,
)
from photometa.presentation.privacy_score import (
    format_privacy_score,
    format_privacy_score_detailed,
)
from photometa.presentation.report import (
    format_full_report,
)
from photometa.presentation.scan import (
    format_scan_report,
    format_segment_report,
)

from photometa.exporters.csv_export import (
    CsvExportError,
    write_batch_csv,
)

from photometa.exporters.json_export import (
    JsonExportError,
    build_batch_scan_json_document,
    build_scan_json_document,
    serialize_json_document,
)

from photometa.exporters.html_report import (
    HtmlReportError,
    write_html_report,
)

from photometa.formats.pillow_backend import (
    FORMAT_JPEG,
    AdditionalFormatError,
    detect_scan_format,
    inspect_additional_image,
)
from photometa.presentation.additional_scan import (
    format_additional_scan_report,
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


DISTRIBUTION_NAME = (
    "photo-metadata-forensics"
)


def get_version() -> str:

    try:

        return version(
            DISTRIBUTION_NAME
        )

    except PackageNotFoundError:

        return "0+unknown"


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

    parser.add_argument(
        "--version",
        action="version",
        version=(
            "%(prog)s "
            + get_version()
        ),
    )

    commands = parser.add_subparsers(
        dest="command",
    )

    scan_parser = commands.add_parser(
        "scan",
        help=(
            "Scan a supported image and summarize "
            "available metadata and structure."
        ),
    )

    scan_parser.add_argument(
        "path",
        type=Path,
        help=("Image file or directory to scan."),
    )

    scan_parser.add_argument(
        "--segments",
        action="store_true",
        help=(
            "Also display JPEG header "
            "segments before the first SOS."
        ),
    )

    scan_parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help=(
            "Recursively scan files when "
            "PATH is a directory."
        ),
    )

    scan_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help=(
            "Output machine-readable "
            "JSON instead of text."
        ),
    )

    scan_parser.add_argument(
        "--include-sensitive",
        action="store_true",
        help=(
            "Include exact GPS values "
            "in single-file JSON output."
        ),
    )

    scan_parser.add_argument(
        "--csv",
        dest="csv_output",
        type=Path,
        default=None,
        metavar="OUTPUT",
        help=(
            "Export a directory scan "
            "to a CSV file."
        ),
    )

    privacy_parser = commands.add_parser(
        "privacy",
        help=(
            "Analyze privacy-sensitive "
            "metadata and exposure score."
        ),
    )

    privacy_parser.add_argument(
        "path",
        type=Path,
        help=(
            "JPEG file to analyze."
        ),
    )

    privacy_parser.add_argument(
        "--detailed",
        action="store_true",
        help=(
            "Show finding sources, fields "
            "and score contributions."
        ),
    )

    privacy_parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help=(
            "Recursively analyze files when "
            "PATH is a directory."
        ),
    )

    gps_parser = commands.add_parser(
        "gps",
        help=(
            "Extract and display GPS "
            "metadata."
        ),
    )

    gps_parser.add_argument(
        "path",
        type=Path,
        help=(
            "JPEG file to inspect."
        ),
    )

    gps_parser.add_argument(
        "--raw",
        action="store_true",
        help=(
            "Also display raw forensic "
            "GPS IFD values."
        ),
    )

    report_parser = commands.add_parser(
        "report",
        help=(
            "Generate a comprehensive "
            "metadata and forensic report."
        ),
    )

    report_parser.add_argument(
        "path",
        type=Path,
        help=(
            "JPEG file to report."
        ),
    )

    report_parser.add_argument(
        "--include-sensitive",
        action="store_true",
        help=(
            "Include exact GPS coordinates "
            "when available."
        ),
    )

    report_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "HTML output path. "
            "Default: report.html"
        ),
    )

    report_parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Replace an existing "
            "HTML output file."
        ),
    )

    report_parser.add_argument(
        "--text",
        action="store_true",
        help=(
            "Print the legacy text report "
            "instead of creating HTML."
        ),
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

    if args.command == "scan":

        try:

            return run_scan_command(
                path=args.path,
                show_segments=(
                    args.segments
                ),
                recursive=(
                    args.recursive
                ),
                json_output=(
                    args.json_output
                ),
                include_sensitive=(
                    args.include_sensitive
                ),
                csv_output=(
                    args.csv_output
                ),
            )

        except (
            AdditionalFormatError,
            BatchAnalysisError,
            ComparisonError,
            CsvExportError,
            JsonExportError,
            JpegParserError,
            OSError,
        ) as exc:

            print(
                f"error: {exc}",
                file=sys.stderr,
            )

            return 1

    if args.command == "privacy":

        try:

            return run_privacy_command(
                path=args.path,
                detailed=(
                    args.detailed
                ),
                recursive=(
                    args.recursive
                ),
            )

        except (
            BatchAnalysisError,
            JpegParserError,
            XmpParserError,
            IptcParserError,
            OSError,
        ) as exc:

            print(
                f"error: {exc}",
                file=sys.stderr,
            )

            return 1

    if args.command == "gps":

        try:

            return run_gps_command(
                path=args.path,
                raw=args.raw,
            )

        except (
            ComparisonError,
            GpsIfdExtractorError,
        ) as exc:

            print(
                f"error: {exc}",
                file=sys.stderr,
            )

            return 1

    if args.command == "report":

        try:

            return run_report_command(
                path=args.path,
                include_sensitive=(
                    args.include_sensitive
                ),
                output=args.output,
                force=args.force,
                text_output=args.text,
            )

        except (
            FullReportError,
            HtmlReportError,
        ) as exc:

            print(
                f"error: {exc}",
                file=sys.stderr,
            )

            return 1

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


def run_scan_command(
    path: Path,
    show_segments: bool = False,
    recursive: bool = False,
    json_output: bool = False,
    include_sensitive: bool = False,
    csv_output: Path | None = None,
) -> int:

    if (
        json_output
        and csv_output is not None
    ):

        raise CsvExportError(
            (
                "--json cannot be combined "
                "with --csv."
            )
        )

    if (
        csv_output is not None
        and show_segments
    ):

        raise CsvExportError(
            (
                "--csv cannot be combined "
                "with --segments."
            )
        )

    if (
        csv_output is not None
        and include_sensitive
    ):

        raise CsvExportError(
            (
                "--include-sensitive is "
                "not available with --csv."
            )
        )

    if (
        json_output
        and show_segments
    ):

        raise JsonExportError(
            (
                "--json cannot be combined "
                "with --segments."
            )
        )

    if (
        include_sensitive
        and not json_output
    ):

        raise JsonExportError(
            (
                "--include-sensitive "
                "requires --json."
            )
        )

    if path.is_dir():

        exclusions: tuple[
            Path,
            ...
        ] = ()

        if csv_output is not None:

            exclusions = (
                csv_output,
            )

        report = analyze_directory(
            path,
            recursive=recursive,
            exclude_paths=(
                exclusions
            ),
        )

        if csv_output is not None:

            result = (
                write_batch_csv(
                    report,
                    csv_output,
                )
            )

            print("CSV EXPORT")
            print("-" * 60)

            print(
                "Directory:  "
                f"{report.root}"
            )

            print(
                "Output:     "
                f"{result.output_path}"
            )

            print(
                "Rows:       "
                f"{result.row_count}"
            )

            print(
                "Recursive:  "
                + (
                    "YES"
                    if recursive
                    else "NO"
                )
            )

            return 0

        if json_output:

            document = (
                build_batch_scan_json_document(
                    report
                )
            )

            print(
                serialize_json_document(
                    document
                )
            )

            return 0

        if show_segments:

            raise BatchAnalysisError(
                (
                    "--segments is only "
                    "available when scanning "
                    "a single JPEG file."
                )
            )

        if include_sensitive:

            raise JsonExportError(
                (
                    "--include-sensitive is "
                    "only available for "
                    "single-file JSON scans."
                )
            )

        print(
            format_batch_scan_report(
                report
            )
        )

        return 0

    if csv_output is not None:

        raise CsvExportError(
            (
                "--csv requires a "
                "directory input."
            )
        )

    format_name = (
        detect_scan_format(
            path
        )
    )

    if format_name != FORMAT_JPEG:

        if show_segments:

            raise AdditionalFormatError(
                (
                    "--segments is a "
                    "JPEG-only operation."
                )
            )

        if json_output:

            raise AdditionalFormatError(
                (
                    "Single-file JSON export "
                    f"is not yet implemented "
                    f"for {format_name}. "
                    "Use the normal scan "
                    "during Point 27A."
                )
            )

        if include_sensitive:

            raise AdditionalFormatError(
                (
                    "--include-sensitive "
                    "is currently available "
                    "only for JPEG JSON scans."
                )
            )

        snapshot = (
            inspect_additional_image(
                path
            )
        )

        print(
            format_additional_scan_report(
                snapshot
            )
        )

        return 0

    if json_output:

        document = (
            build_scan_json_document(
                path,
                include_sensitive=(
                    include_sensitive
                ),
            )
        )

        print(
            serialize_json_document(
                document
            )
        )

        return 0

    snapshot = (
        inspect_image_for_comparison(
            path
        )
    )

    print(
        format_scan_report(
            snapshot
        )
    )

    if show_segments:

        segments = tuple(
            iter_jpeg_segments(
                path
            )
        )

        print()

        print(
            format_segment_report(
                segments
            )
        )

    return 0


def run_privacy_command(
    path: Path,
    detailed: bool = False,
    recursive: bool = False,
) -> int:

    if path.is_dir():

        report = analyze_directory(
            path,
            recursive=recursive,
        )

        print(
            format_batch_privacy_report(
                report,
                detailed=detailed,
            )
        )

        return 0

    report = analyze_privacy(
        path
    )

    score = (
        calculate_privacy_exposure_score(
            report
        )
    )

    if detailed:

        privacy_text = (
            format_privacy_detailed_report(
                report
            )
        )

        score_text = (
            format_privacy_score_detailed(
                score
            )
        )

    else:

        privacy_text = (
            format_privacy_report(
                report
            )
        )

        score_text = (
            format_privacy_score(
                score
            )
        )

    print(
        privacy_text
    )

    print()

    print(
        score_text
    )

    return 0


def run_gps_command(
    path: Path,
    raw: bool = False,
) -> int:

    snapshot = (
        inspect_image_for_comparison(
            path
        )
    )

    if snapshot.gps == PRESENCE_NO:

        print("LOCATION")
        print("-" * 45)
        print("GPS detected: NO")

        return 0

    if (
        snapshot.gps
        == PRESENCE_UNKNOWN
    ):

        raise GpsIfdExtractorError(
            (
                "GPS status could not be "
                "determined because EXIF "
                "could not be fully parsed."
            )
        )

    metadata = (
        extract_gps_ifd_from_jpeg(
            path
        )
    )

    summary = (
        build_location_summary(
            metadata
        )
    )

    print(
        format_location_report(
            summary
        )
    )

    if raw:

        print()

        print(
            format_gps_raw_report(
                metadata
            )
        )

    return 0


def run_report_command(
    path: Path,
    include_sensitive: bool = False,
    output: Path | None = None,
    force: bool = False,
    text_output: bool = False,
) -> int:

    if text_output:

        if output is not None:

            raise HtmlReportError(
                (
                    "--output cannot be "
                    "combined with --text."
                )
            )

        if force:

            raise HtmlReportError(
                (
                    "--force cannot be "
                    "combined with --text."
                )
            )

        report = build_full_report(
            path
        )

        print(
            format_full_report(
                report,
                include_sensitive=(
                    include_sensitive
                ),
            )
        )

        return 0

    destination = (
        output
        if output is not None
        else Path(
            "report.html"
        )
    )

    written = write_html_report(
        path,
        destination,
        include_sensitive=(
            include_sensitive
        ),
        force=force,
    )

    print("HTML REPORT")
    print("-" * 60)

    print(
        f"Source:    {path}"
    )

    print(
        f"Output:    {written}"
    )

    print(
        "GPS data:  "
        + (
            "included"
            if include_sensitive
            else "exact coordinates hidden"
        )
    )

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
