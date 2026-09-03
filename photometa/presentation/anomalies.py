from __future__ import annotations

from photometa.analysis.anomalies import (
    AnomalyReport,
)


def format_anomaly_report(
    report: AnomalyReport,
) -> str:

    lines = [
        "ANOMALIES",
        "-" * 60,
    ]

    if not report.findings:

        lines.append(
            (
                "✓ No anomalies detected "
                "by the current rule set."
            )
        )

    else:

        for finding in (
            report.findings
        ):

            lines.append(
                f"⚠ {finding.message}"
            )

            if finding.evidence:

                lines.append(
                    (
                        "  Evidence: "
                        + "; ".join(
                            finding.evidence
                        )
                    )
                )

    lines.extend(
        (
            "",
            (
                "This does not prove "
                "image manipulation."
            ),
            (
                "Anomalies may result from "
                "normal software behavior, "
                "exports, incomplete metadata, "
                "device-specific behavior, "
                "or malformed metadata."
            ),
        )
    )

    return "\n".join(
        lines
    )


def format_anomaly_detailed_report(
    report: AnomalyReport,
) -> str:

    lines = [
        "ANOMALIES",
        "-" * 60,
    ]

    if not report.findings:

        lines.append(
            (
                "✓ No anomalies detected "
                "by the current rule set."
            )
        )

    else:

        for finding in (
            report.findings
        ):

            lines.append(
                (
                    f"⚠ [{finding.severity.upper()}] "
                    f"{finding.message}"
                )
            )

            lines.append(
                (
                    "  Category: "
                    f"{finding.category}"
                )
            )

            if finding.evidence:

                lines.append(
                    (
                        "  Evidence: "
                        + "; ".join(
                            finding.evidence
                        )
                    )
                )

    lines.extend(
        (
            "",
            (
                "This does not prove "
                "image manipulation."
            ),
            (
                "A finding is an indicator "
                "for further examination, "
                "not a conclusion about "
                "authenticity or provenance."
            ),
        )
    )

    return "\n".join(
        lines
    )
