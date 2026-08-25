from __future__ import annotations

from photometa.analysis.privacy_score import (
    PrivacyExposureScore,
)


DEFAULT_BAR_WIDTH = 10


def format_privacy_score(
    score: PrivacyExposureScore,
) -> str:

    bar = build_score_bar(
        score.percentage,
        width=DEFAULT_BAR_WIDTH,
    )

    lines = [
        "PRIVACY EXPOSURE SCORE",
        "-" * 60,
        (
            f"Exposure: "
            f"{score.level} "
            f"{bar} "
            f"{score.points}/"
            f"{score.maximum}"
        ),
        "",
        (
            "This is a rule-based metadata "
            "exposure index, not a probability "
            "of harm or forensic certainty."
        ),
    ]

    return "\n".join(
        lines
    )


def format_privacy_score_detailed(
    score: PrivacyExposureScore,
) -> str:

    bar = build_score_bar(
        score.percentage,
        width=DEFAULT_BAR_WIDTH,
    )

    lines = [
        "PRIVACY EXPOSURE SCORE",
        "-" * 60,
        (
            f"Exposure: "
            f"{score.level} "
            f"{bar} "
            f"{score.points}/"
            f"{score.maximum}"
        ),
        (
            f"Matrix version: "
            f"{score.version}"
        ),
        "",
        "SCORING CONTRIBUTIONS",
        "-" * 60,
    ]

    if score.contributions:

        for contribution in (
            score.contributions
        ):

            lines.append(
                (
                    f"+{contribution.points:<3} "
                    f"{contribution.label}"
                )
            )

    else:

        lines.append(
            "No scored exposure rules matched."
        )

    if score.unscored_findings:

        lines.extend(
            (
                "",
                "UNSCORED FINDINGS",
                "-" * 60,
            )
        )

        for code in (
            score.unscored_findings
        ):

            lines.append(
                f"• {code}"
            )

    lines.extend(
        (
            "",
            (
                "Important: this value is a "
                "weighted metadata exposure "
                "index."
            ),
            (
                "It is NOT the probability of "
                "harm, compromise, tracking, "
                "identification, or malicious "
                "use."
            ),
        )
    )

    return "\n".join(
        lines
    )


def build_score_bar(
    percentage: int,
    width: int = DEFAULT_BAR_WIDTH,
) -> str:

    if width <= 0:
        raise ValueError(
            "Score bar width must "
            "be greater than zero."
        )

    bounded_percentage = max(
        0,
        min(
            percentage,
            100,
        ),
    )

    filled = (
        bounded_percentage
        * width
        + 50
    ) // 100

    empty = (
        width
        - filled
    )

    return (
        "█" * filled
        + "░" * empty
    )
