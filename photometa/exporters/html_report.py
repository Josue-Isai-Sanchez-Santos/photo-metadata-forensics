from __future__ import annotations

import html
import os
import tempfile
from fractions import Fraction
from pathlib import Path

from photometa.analysis.report import (
    FullReport,
    FullReportError,
    build_full_report,
)
from photometa.extractors.exif_ifd import (
    ExifIfdExtractorError,
    ExifIfdMetadata,
    build_capture_summary,
    extract_exif_ifd_from_jpeg,
)
from photometa.extractors.ifd0 import (
    Ifd0ExtractorError,
    extract_ifd0_from_jpeg,
)
from photometa.hashing import (
    HashingError,
    calculate_hashes,
)
from photometa.interpretation.special_fields import (
    interpret_special_field,
)
from photometa.parsers.exif import (
    ExifParserError,
)
from photometa.parsers.jpeg import (
    JpegParserError,
)
from photometa.parsers.tiff import (
    TiffParserError,
)


class HtmlReportError(Exception):
    """Base exception for HTML report errors."""


OPTIONAL_EXIF_ERRORS = (
    Ifd0ExtractorError,
    ExifIfdExtractorError,
    ExifParserError,
    TiffParserError,
    JpegParserError,
    OSError,
)


def build_html_report(
    path: str | Path,
    *,
    include_sensitive: bool = False,
) -> str:

    file_path = Path(
        path
    )

    try:

        report = build_full_report(
            file_path
        )

    except FullReportError as exc:

        raise HtmlReportError(
            str(exc)
        ) from exc

    try:

        hashes = calculate_hashes(
            file_path,
            (
                "sha256",
                "sha1",
                "md5",
            ),
        )

    except HashingError as exc:

        raise HtmlReportError(
            (
                "Could not calculate "
                f"report hashes: {exc}"
            )
        ) from exc

    warnings = list(
        report.scan.warnings
    )

    ifd0_values: dict[
        str,
        object,
    ] = {}

    exif_values: dict[
        str,
        object,
    ] = {}

    exif_metadata: (
        ExifIfdMetadata
        | None
    ) = None

    try:

        ifd0 = (
            extract_ifd0_from_jpeg(
                file_path
            )
        )

        ifd0_values = (
            ifd0.as_dict()
        )

    except OPTIONAL_EXIF_ERRORS as exc:

        if (
            report.scan.exif
            == "YES"
        ):

            warnings.append(
                (
                    "IFD0 could not be "
                    f"fully exported: {exc}"
                )
            )

    try:

        exif_metadata = (
            extract_exif_ifd_from_jpeg(
                file_path
            )
        )

        exif_values = (
            exif_metadata.as_dict()
        )

    except OPTIONAL_EXIF_ERRORS as exc:

        if (
            report.scan.exif
            == "YES"
        ):

            warnings.append(
                (
                    "ExifIFD could not be "
                    f"fully exported: {exc}"
                )
            )

    gps_values: dict[
        str,
        object,
    ] = {}

    if (
        report.gps_metadata
        is not None
    ):

        gps_values = (
            report.gps_metadata.as_dict()
        )

    interpretations = (
        _build_interpretations(
            ifd0_values,
            exif_values,
            gps_values,
        )
    )

    capture = (
        build_capture_summary(
            exif_metadata
        )
        if exif_metadata
        is not None
        else None
    )

    return _render_document(
        report=report,
        hashes=hashes,
        ifd0_values=ifd0_values,
        exif_values=exif_values,
        gps_values=gps_values,
        interpretations=(
            interpretations
        ),
        capture=capture,
        warnings=tuple(
            dict.fromkeys(
                warnings
            )
        ),
        include_sensitive=(
            include_sensitive
        ),
    )


def write_html_report(
    path: str | Path,
    output_path: str | Path,
    *,
    include_sensitive: bool = False,
    force: bool = False,
) -> Path:

    output = Path(
        output_path
    ).resolve()

    if (
        output.exists()
        and not force
    ):

        raise HtmlReportError(
            (
                "Output already exists: "
                f"{output}. Use --force "
                "to replace it."
            )
        )

    if (
        not output.parent.exists()
    ):

        raise HtmlReportError(
            (
                "Output directory does "
                f"not exist: {output.parent}"
            )
        )

    document = build_html_report(
        path,
        include_sensitive=(
            include_sensitive
        ),
    )

    temporary: (
        Path
        | None
    ) = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output.parent,
            prefix=(
                f".{output.name}."
            ),
            suffix=".tmp",
            delete=False,
        ) as file:

            temporary = Path(
                file.name
            )

            file.write(
                document
            )

        os.replace(
            temporary,
            output,
        )

    except OSError as exc:

        if (
            temporary is not None
            and temporary.exists()
        ):

            try:

                temporary.unlink()

            except OSError:
                pass

        raise HtmlReportError(
            (
                "Could not write HTML "
                f"report: {exc}"
            )
        ) from exc

    return output


def _render_document(
    *,
    report: FullReport,
    hashes: dict[str, str],
    ifd0_values: dict[str, object],
    exif_values: dict[str, object],
    gps_values: dict[str, object],
    interpretations: tuple[
        tuple[
            str,
            str,
            object,
            str,
        ],
        ...,
    ],
    capture: object | None,
    warnings: tuple[str, ...],
    include_sensitive: bool,
) -> str:

    info = report.file_info

    title = (
        "PhotoMeta Report — "
        f"{info.name}"
    )

    sections = [
        _section(
            "File Information",
            _table(
                (
                    ("Name", info.name),
                    ("Path", info.path),
                    ("Type", info.file_type),
                    ("Format", info.format),
                    ("MIME type", info.mime_type),
                    ("Size", info.size_human),
                    ("Size bytes", info.size_bytes),
                    ("Resolution", info.resolution),
                    (
                        "JPEG process",
                        report.scan.jpeg_process,
                    ),
                    (
                        "Modified",
                        info.modified_at.isoformat(),
                    ),
                    (
                        "Accessed",
                        info.accessed_at.isoformat(),
                    ),
                    (
                        "Metadata changed",
                        (
                            info.metadata_changed_at.isoformat()
                            if info.metadata_changed_at
                            is not None
                            else None
                        ),
                    ),
                    (
                        "Created",
                        (
                            info.created_at.isoformat()
                            if info.created_at
                            is not None
                            else None
                        ),
                    ),
                )
            )
            + (
                "<p class=\"note\">"
                "Filesystem timestamps are not "
                "EXIF capture timestamps."
                "</p>"
            ),
        ),
        _section(
            "Metadata Presence",
            _table(
                (
                    ("EXIF", report.scan.exif),
                    ("GPS", report.scan.gps),
                    ("XMP", report.scan.xmp),
                    ("IPTC", report.scan.iptc),
                    ("ICC", report.scan.icc),
                    (
                        "Camera model",
                        report.scan.camera_model,
                    ),
                )
            ),
        ),
        _section(
            "Hashes",
            _table(
                (
                    (
                        "SHA-256",
                        hashes.get(
                            "sha256"
                        ),
                    ),
                    (
                        "SHA-1",
                        hashes.get(
                            "sha1"
                        ),
                    ),
                    (
                        "MD5",
                        hashes.get(
                            "md5"
                        ),
                    ),
                )
            )
            + (
                "<p class=\"note\">"
                "Hashes identify file bytes. "
                "They do not establish image "
                "authenticity or provenance."
                "</p>"
            ),
        ),
        _section(
            "Capture",
            _capture_html(
                capture
            ),
        ),
        _section(
            "EXIF — IFD0",
            _metadata_table(
                ifd0_values
            ),
        ),
        _section(
            "EXIF — ExifIFD",
            _metadata_table(
                exif_values
            ),
        ),
        _section(
            "Location",
            _location_html(
                report,
                gps_values=(
                    gps_values
                ),
                include_sensitive=(
                    include_sensitive
                ),
            ),
        ),
        _section(
            "Privacy",
            _privacy_html(
                report
            ),
        ),
        _section(
            "Anomalies",
            _anomalies_html(
                report
            ),
        ),
        _section(
            "Interpretation of Special Values",
            _interpretation_html(
                interpretations
            ),
        ),
    ]

    if warnings:

        sections.append(
            _section(
                "Warnings",
                "<ul>"
                + "".join(
                    (
                        "<li>"
                        + _escape(
                            warning
                        )
                        + "</li>"
                    )
                    for warning
                    in warnings
                )
                + "</ul>",
            )
        )

    sections.append(
        _section(
            "Interpretation Notes",
            (
                "<p>"
                "PhotoMeta reports supported "
                "metadata and structural "
                "observations. An anomaly does "
                "not prove manipulation, and "
                "the absence of anomalies does "
                "not prove authenticity."
                "</p>"
                "<p>"
                "Privacy Exposure Score is a "
                "rule-based metadata exposure "
                "index, not a probability of "
                "harm, tracking, compromise, "
                "or identification."
                "</p>"
            ),
        )
    )

    sensitive_text = (
        "Exact GPS values included."
        if include_sensitive
        else (
            "Exact GPS coordinates are "
            "hidden by default."
        )
    )

    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" "
        "content=\"width=device-width,"
        "initial-scale=1\">\n"
        f"<title>{_escape(title)}</title>\n"
        "<style>\n"
        ":root{color-scheme:light dark;"
        "font-family:system-ui,-apple-system,"
        "BlinkMacSystemFont,'Segoe UI',sans-serif}"
        "body{margin:0;background:#f3f4f6;"
        "color:#111827}"
        "main{max-width:1100px;margin:0 auto;"
        "padding:32px 18px 64px}"
        "header{background:#111827;color:white;"
        "padding:28px;border-radius:16px;"
        "margin-bottom:20px}"
        "header h1{margin:0 0 8px;font-size:2rem}"
        "header p{margin:4px 0;color:#d1d5db}"
        "section{background:white;padding:22px;"
        "border-radius:14px;margin:16px 0;"
        "box-shadow:0 1px 4px rgba(0,0,0,.08)}"
        "h2{margin-top:0;font-size:1.25rem}"
        "table{width:100%;border-collapse:collapse;"
        "font-size:.94rem}"
        "th,td{text-align:left;vertical-align:top;"
        "padding:9px;border-bottom:1px solid #e5e7eb;"
        "overflow-wrap:anywhere}"
        "th{width:28%;font-weight:650}"
        ".mono{font-family:ui-monospace,SFMono-Regular,"
        "Menlo,Consolas,monospace}"
        ".note{padding:10px 12px;border-left:4px "
        "solid #6b7280;background:#f9fafb}"
        ".high{font-weight:700}"
        ".muted{color:#6b7280}"
        "ul{padding-left:22px}"
        "@media(prefers-color-scheme:dark){"
        "body{background:#0f172a;color:#e5e7eb}"
        "section{background:#1e293b}"
        "th,td{border-color:#334155}"
        ".note{background:#111827}"
        ".muted{color:#94a3b8}"
        "}"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "<main>\n"
        "<header>\n"
        "<h1>PhotoMeta Report</h1>\n"
        f"<p>{_escape(info.name)}</p>\n"
        f"<p>{_escape(sensitive_text)}</p>\n"
        "</header>\n"
        + "\n".join(
            sections
        )
        + "\n</main>\n"
        "</body>\n"
        "</html>\n"
    )


def _section(
    title: str,
    body: str,
) -> str:

    return (
        "<section>"
        f"<h2>{_escape(title)}</h2>"
        f"{body}"
        "</section>"
    )


def _table(
    rows: tuple[
        tuple[
            str,
            object,
        ],
        ...,
    ],
) -> str:

    return (
        "<table><tbody>"
        + "".join(
            (
                "<tr>"
                f"<th>{_escape(label)}</th>"
                f"<td>{_escape_value(value)}</td>"
                "</tr>"
            )
            for label, value
            in rows
        )
        + "</tbody></table>"
    )


def _metadata_table(
    values: dict[
        str,
        object,
    ],
) -> str:

    if not values:

        return (
            "<p class=\"muted\">"
            "No supported values available."
            "</p>"
        )

    rows = tuple(
        (
            name,
            value,
        )
        for name, value
        in sorted(
            values.items(),
            key=lambda item: (
                item[0].casefold()
            ),
        )
    )

    return _table(
        rows
    )


def _capture_html(
    capture: object | None,
) -> str:

    if capture is None:

        return (
            "<p class=\"muted\">"
            "No normalized capture summary "
            "is available."
            "</p>"
        )

    return _table(
        (
            (
                "Date",
                getattr(
                    capture,
                    "date",
                    None,
                ),
            ),
            (
                "Time",
                getattr(
                    capture,
                    "time",
                    None,
                ),
            ),
            (
                "Exposure",
                getattr(
                    capture,
                    "exposure",
                    None,
                ),
            ),
            (
                "ISO",
                getattr(
                    capture,
                    "iso",
                    None,
                ),
            ),
            (
                "Aperture",
                getattr(
                    capture,
                    "aperture",
                    None,
                ),
            ),
            (
                "Focal length",
                getattr(
                    capture,
                    "focal_length",
                    None,
                ),
            ),
            (
                "Lens",
                getattr(
                    capture,
                    "lens",
                    None,
                ),
            ),
        )
    )


def _location_html(
    report: FullReport,
    *,
    gps_values: dict[
        str,
        object,
    ],
    include_sensitive: bool,
) -> str:

    if report.gps_error is not None:

        return (
            "<p>"
            "<strong>GPS status:</strong> ERROR"
            "</p>"
            "<p>"
            + _escape(
                report.gps_error
            )
            + "</p>"
        )

    if report.gps_summary is None:

        return (
            "<p>GPS metadata detected: "
            "<strong>NO</strong></p>"
        )

    if not include_sensitive:

        return (
            "<p>GPS metadata detected: "
            "<strong>YES</strong></p>"
            "<p class=\"note\">"
            "Exact coordinates and raw GPS "
            "values are hidden. Re-run with "
            "<span class=\"mono\">"
            "--include-sensitive"
            "</span> to include them."
            "</p>"
        )

    gps = report.gps_summary

    human = _table(
        (
            ("Latitude", gps.latitude),
            ("Longitude", gps.longitude),
            (
                "Altitude",
                (
                    f"{gps.altitude} m"
                    if gps.altitude
                    is not None
                    else None
                ),
            ),
            (
                "Altitude reference",
                gps.altitude_reference,
            ),
            ("GPS date", gps.gps_date),
            ("GPS time", gps.gps_time),
            (
                "Image direction",
                gps.image_direction,
            ),
        )
    )

    return (
        human
        + "<h3>Raw GPS EXIF</h3>"
        + _metadata_table(
            gps_values
        )
    )


def _privacy_html(
    report: FullReport,
) -> str:

    score = report.privacy_score

    body = (
        _table(
            (
                (
                    "Exposure level",
                    score.level,
                ),
                (
                    "Score",
                    (
                        f"{score.points}/"
                        f"{score.maximum}"
                    ),
                ),
                (
                    "Score matrix",
                    score.version,
                ),
            )
        )
        + (
            "<progress value=\""
            f"{score.points}"
            "\" max=\""
            f"{score.maximum}"
            "\"></progress>"
        )
    )

    if not report.privacy.findings:

        return (
            body
            + "<p>No supported privacy "
            "findings detected.</p>"
        )

    body += (
        "<table><thead><tr>"
        "<th>Severity</th>"
        "<th>Finding</th>"
        "<th>Sources</th>"
        "<th>Fields</th>"
        "</tr></thead><tbody>"
    )

    for finding in (
        report.privacy.findings
    ):

        body += (
            "<tr>"
            f"<td>{_escape(finding.severity.upper())}</td>"
            f"<td>{_escape(finding.message)}</td>"
            "<td>"
            + _escape(
                ", ".join(
                    finding.sources
                )
            )
            + "</td>"
            "<td>"
            + _escape(
                ", ".join(
                    finding.fields
                )
            )
            + "</td>"
            "</tr>"
        )

    return (
        body
        + "</tbody></table>"
    )


def _anomalies_html(
    report: FullReport,
) -> str:

    if not report.anomalies.findings:

        return (
            "<p>No anomalies detected by "
            "the current rule set.</p>"
            "<p class=\"note\">"
            "This does not prove authenticity "
            "or originality."
            "</p>"
        )

    body = (
        "<table><thead><tr>"
        "<th>Severity</th>"
        "<th>Category</th>"
        "<th>Finding</th>"
        "<th>Evidence</th>"
        "</tr></thead><tbody>"
    )

    for finding in (
        report.anomalies.findings
    ):

        body += (
            "<tr>"
            f"<td>{_escape(finding.severity.upper())}</td>"
            f"<td>{_escape(finding.category)}</td>"
            f"<td>{_escape(finding.message)}</td>"
            "<td>"
            + _escape(
                "; ".join(
                    finding.evidence
                )
            )
            + "</td>"
            "</tr>"
        )

    return (
        body
        + "</tbody></table>"
        + "<p class=\"note\">"
        "Anomalies are investigative "
        "indicators and do not prove "
        "manipulation."
        "</p>"
    )


def _build_interpretations(
    ifd0: dict[str, object],
    exif: dict[str, object],
    gps: dict[str, object],
) -> tuple[
    tuple[
        str,
        str,
        object,
        str,
    ],
    ...,
]:

    requested = (
        (
            "IFD0",
            ifd0,
            (
                "Orientation",
            ),
        ),
        (
            "ExifIFD",
            exif,
            (
                "ExposureProgram",
                "MeteringMode",
                "Flash",
                "WhiteBalance",
                "SceneCaptureType",
                "ColorSpace",
            ),
        ),
        (
            "GPS",
            gps,
            (
                "GPSAltitudeRef",
            ),
        ),
    )

    result: list[
        tuple[
            str,
            str,
            object,
            str,
        ]
    ] = []

    for (
        source,
        values,
        fields,
    ) in requested:

        for field in fields:

            if field not in values:

                continue

            raw = values[
                field
            ]

            result.append(
                (
                    source,
                    field,
                    raw,
                    interpret_special_field(
                        field,
                        raw,
                    ),
                )
            )

    return tuple(
        result
    )


def _interpretation_html(
    rows: tuple[
        tuple[
            str,
            str,
            object,
            str,
        ],
        ...,
    ],
) -> str:

    if not rows:

        return (
            "<p class=\"muted\">"
            "No supported special fields "
            "were available for interpretation."
            "</p>"
        )

    body = (
        "<table><thead><tr>"
        "<th>Source</th>"
        "<th>Field</th>"
        "<th>Raw value</th>"
        "<th>Interpretation</th>"
        "</tr></thead><tbody>"
    )

    for (
        source,
        field,
        raw,
        interpreted,
    ) in rows:

        body += (
            "<tr>"
            f"<td>{_escape(source)}</td>"
            f"<td>{_escape(field)}</td>"
            f"<td>{_escape_value(raw)}</td>"
            f"<td>{_escape(interpreted)}</td>"
            "</tr>"
        )

    return (
        body
        + "</tbody></table>"
        + "<p class=\"note\">"
        "Interpretation does not modify "
        "the original raw metadata value."
        "</p>"
    )


def _escape(
    value: object,
) -> str:

    return html.escape(
        str(value),
        quote=True,
    )


def _escape_value(
    value: object,
) -> str:

    if value is None:

        return (
            "<span class=\"muted\">"
            "Not available"
            "</span>"
        )

    return _escape(
        _format_raw_value(
            value
        )
    )


def _format_raw_value(
    value: object,
) -> str:

    if isinstance(
        value,
        Fraction,
    ):

        return (
            f"{value.numerator}/"
            f"{value.denominator}"
        )

    if isinstance(
        value,
        bytes,
    ):

        return (
            "0x"
            + value.hex()
        )

    if isinstance(
        value,
        tuple,
    ):

        return (
            "("
            + ", ".join(
                _format_raw_value(
                    item
                )
                for item
                in value
            )
            + ")"
        )

    return str(
        value
    )
