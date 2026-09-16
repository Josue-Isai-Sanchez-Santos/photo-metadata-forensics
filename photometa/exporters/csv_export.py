from __future__ import annotations

import csv
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from photometa.analysis.batch import (
    BatchFileResult,
    BatchReport,
)

CSV_SCHEMA_VERSION = "1.0"

CSV_COLUMNS = (
    "schema_version",
    "path",
    "format",
    "analyzed",
    "size_bytes",
    "sha256",
    "width",
    "height",
    "jpeg_process",
    "metadata_exif",
    "metadata_gps",
    "metadata_xmp",
    "metadata_iptc",
    "metadata_icc",
    "camera_model",
    "gps_detected",
    "privacy_level",
    "privacy_points",
    "error",
)


class CsvExportError(Exception):
    """Base exception for CSV export errors."""


@dataclass(frozen=True)
class CsvExportResult:
    output_path: Path
    row_count: int


def write_batch_csv(
    report: BatchReport,
    output_path: str | Path,
) -> CsvExportResult:

    output = Path(
        output_path
    ).resolve()

    parent = output.parent

    if not parent.exists():

        raise CsvExportError(
            (
                "CSV output directory "
                f"does not exist: {parent}"
            )
        )

    if not parent.is_dir():

        raise CsvExportError(
            (
                "CSV output parent is "
                f"not a directory: {parent}"
            )
        )

    if (
        output.exists()
        and output.is_dir()
    ):

        raise CsvExportError(
            (
                "CSV output path is "
                f"a directory: {output}"
            )
        )

    temporary_path: (
        Path
        | None
    ) = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=parent,
            prefix=(
                f".{output.name}."
            ),
            suffix=".tmp",
            delete=False,
        ) as file:

            temporary_path = Path(
                file.name
            )

            writer = csv.DictWriter(
                file,
                fieldnames=(
                    CSV_COLUMNS
                ),
                extrasaction="raise",
            )

            writer.writeheader()

            for item in (
                report.items
            ):

                writer.writerow(
                    _build_csv_row(
                        report,
                        item,
                    )
                )

        os.replace(
            temporary_path,
            output,
        )

    except (
        OSError,
        csv.Error,
        ValueError,
    ) as exc:

        if (
            temporary_path
            is not None
            and temporary_path.exists()
        ):

            try:

                temporary_path.unlink()

            except OSError:
                pass

        raise CsvExportError(
            (
                "Could not write CSV "
                f"export: {exc}"
            )
        ) from exc

    return CsvExportResult(
        output_path=output,
        row_count=len(
            report.items
        ),
    )


def _build_csv_row(
    report: BatchReport,
    item: BatchFileResult,
) -> dict[
    str,
    object,
]:

    try:

        relative_path = str(
            item.path.relative_to(
                report.root
            )
        )

    except ValueError:

        relative_path = str(
            item.path
        )

    return {
        "schema_version": (
            CSV_SCHEMA_VERSION
        ),
        "path": (
            relative_path
        ),
        "format": (
            item.detected_format
        ),
        "analyzed": (
            _bool_text(
                item.analyzed_successfully
            )
        ),
        "size_bytes": (
            _value_or_empty(
                item.size_bytes
            )
        ),
        "sha256": (
            item.sha256
            or ""
        ),
        "width": (
            _value_or_empty(
                item.width
            )
        ),
        "height": (
            _value_or_empty(
                item.height
            )
        ),
        "jpeg_process": (
            item.jpeg_process
            or ""
        ),
        "metadata_exif": (
            item.exif_status
            or ""
        ),
        "metadata_gps": (
            item.gps_status
            or ""
        ),
        "metadata_xmp": (
            item.xmp_status
            or ""
        ),
        "metadata_iptc": (
            item.iptc_status
            or ""
        ),
        "metadata_icc": (
            item.icc_status
            or ""
        ),
        "camera_model": (
            item.camera_model
            or ""
        ),
        "gps_detected": (
            _bool_text(
                item.gps_detected
            )
        ),
        "privacy_level": (
            item.privacy_level
            or ""
        ),
        "privacy_points": (
            _value_or_empty(
                item.privacy_points
            )
        ),
        "error": (
            item.error
            or ""
        ),
    }


def _bool_text(
    value: bool | None,
) -> str:

    if value is True:

        return "YES"

    if value is False:

        return "NO"

    return ""


def _value_or_empty(
    value: object | None,
) -> object:

    if value is None:

        return ""

    return value
