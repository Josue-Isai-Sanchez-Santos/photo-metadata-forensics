from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from photometa.analysis.privacy import (
    PrivacyReport,
    analyze_privacy,
)

SCORE_VERSION = "1.0"

LEVEL_LOW = "LOW"
LEVEL_MEDIUM = "MEDIUM"
LEVEL_HIGH = "HIGH"


@dataclass(frozen=True)
class PrivacyScoreRule:
    code: str
    points: int
    label: str


@dataclass(frozen=True)
class PrivacyScoreContribution:
    code: str
    points: int
    label: str


@dataclass(frozen=True)
class PrivacyExposureScore:
    points: int
    maximum: int
    level: str
    contributions: tuple[
        PrivacyScoreContribution,
        ...
    ]
    unscored_findings: tuple[
        str,
        ...
    ]
    version: str = SCORE_VERSION

    @property
    def percentage(
        self,
    ) -> int:
        """
        Percentage of the documented
        scoring matrix.

        This is NOT a probability of harm,
        compromise, identification, or any
        other real-world event.
        """

        if self.maximum <= 0:
            return 0

        return round(
            (
                self.points
                / self.maximum
            )
            * 100
        )


PRIVACY_SCORE_RULES: tuple[
    PrivacyScoreRule,
    ...
] = (
    PrivacyScoreRule(
        code="gps_coordinates",
        points=40,
        label="GPS coordinates",
    ),
    PrivacyScoreRule(
        code="serial_number",
        points=20,
        label="Device or lens serial number",
    ),
    PrivacyScoreRule(
        code="original_capture_date",
        points=10,
        label="Original capture date",
    ),
    PrivacyScoreRule(
        code="device_model",
        points=10,
        label="Device model",
    ),
    PrivacyScoreRule(
        code="owner_information",
        points=10,
        label="Owner or creator information",
    ),
    PrivacyScoreRule(
        code="software",
        points=5,
        label="Software information",
    ),
    PrivacyScoreRule(
        code="copyright_author",
        points=5,
        label="Copyright or author information",
    ),
)


MAX_PRIVACY_SCORE = sum(
    rule.points
    for rule
    in PRIVACY_SCORE_RULES
)


if MAX_PRIVACY_SCORE != 100:
    raise RuntimeError(
        "Privacy score matrix must "
        "total exactly 100 points."
    )


RULES_BY_CODE = {
    rule.code: rule
    for rule
    in PRIVACY_SCORE_RULES
}


def calculate_privacy_exposure_score(
    report: PrivacyReport,
) -> PrivacyExposureScore:
    """
    Calculates a rule-based metadata
    exposure score.

    The resulting 0-100 value represents
    points in a documented scoring matrix.

    It must NOT be interpreted as a
    probability of harm, compromise,
    tracking, identification, or forensic
    certainty.
    """

    finding_codes = {
        finding.code
        for finding
        in report.findings
    }

    contributions: list[
        PrivacyScoreContribution
    ] = []

    for rule in PRIVACY_SCORE_RULES:

        if rule.code not in finding_codes:
            continue

        contributions.append(
            PrivacyScoreContribution(
                code=rule.code,
                points=rule.points,
                label=rule.label,
            )
        )

    points = sum(
        contribution.points
        for contribution
        in contributions
    )

    points = min(
        points,
        MAX_PRIVACY_SCORE,
    )

    scored_codes = {
        contribution.code
        for contribution
        in contributions
    }

    unscored_findings = tuple(
        sorted(
            finding_codes
            - scored_codes
        )
    )

    return PrivacyExposureScore(
        points=points,
        maximum=MAX_PRIVACY_SCORE,
        level=_score_level(
            points
        ),
        contributions=tuple(
            contributions
        ),
        unscored_findings=(
            unscored_findings
        ),
    )


def analyze_privacy_exposure(
    path: str | Path,
) -> PrivacyExposureScore:
    """
    Convenience function that performs
    privacy analysis and then calculates
    the exposure score.
    """

    report = analyze_privacy(
        path
    )

    return (
        calculate_privacy_exposure_score(
            report
        )
    )


def _score_level(
    points: int,
) -> str:

    if points >= 50:
        return LEVEL_HIGH

    if points >= 25:
        return LEVEL_MEDIUM

    return LEVEL_LOW
