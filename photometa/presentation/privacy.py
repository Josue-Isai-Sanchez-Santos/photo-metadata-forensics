from __future__ import annotations

from photometa.analysis.privacy import (
    PrivacyReport,
)


def format_privacy_report(
    report: PrivacyReport,
) -> str:

    lines = [
        "PRIVACY ANALYSIS",
        "-" * 50,
    ]

    if not report.findings:

        lines.append(
            "✓ No obvious privacy-sensitive "
            "metadata detected"
        )

        return "\n".join(
            lines
        )

    for finding in report.findings:

        lines.append(
            f"⚠ {finding.message}"
        )

    return "\n".join(
        lines
    )


def format_privacy_detailed_report(
    report: PrivacyReport,
) -> str:

    lines = [
        "PRIVACY ANALYSIS",
        "-" * 50,
    ]

    if not report.findings:

        lines.append(
            "✓ No obvious privacy-sensitive "
            "metadata detected"
        )

        return "\n".join(
            lines
        )

    for finding in report.findings:

        sources = ", ".join(
            finding.sources
        )

        fields = ", ".join(
            finding.fields
        )

        lines.append(
            (
                f"⚠ [{finding.severity.upper()}] "
                f"{finding.message}"
            )
        )

        lines.append(
            f"  Source: {sources}"
        )

        lines.append(
            f"  Fields: {fields}"
        )

    return "\n".join(
        lines
    )
