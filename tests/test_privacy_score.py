import unittest

from photometa.analysis.privacy import (
    PrivacyFinding,
    PrivacyReport,
)
from photometa.analysis.privacy_score import (
    MAX_PRIVACY_SCORE,
    PRIVACY_SCORE_RULES,
    calculate_privacy_exposure_score,
)
from photometa.presentation.privacy_score import (
    build_score_bar,
    format_privacy_score,
    format_privacy_score_detailed,
)


def make_finding(
    code: str,
) -> PrivacyFinding:

    return PrivacyFinding(
        code=code,
        severity="test",
        message=code,
        sources=("TEST",),
        fields=("TestField",),
    )


def make_report(
    *codes: str,
) -> PrivacyReport:

    return PrivacyReport(
        findings=tuple(
            make_finding(
                code
            )
            for code
            in codes
        )
    )


class TestPrivacyScore(
    unittest.TestCase
):

    def test_matrix_totals_100_points(
        self,
    ):

        self.assertEqual(
            MAX_PRIVACY_SCORE,
            100,
        )

        self.assertEqual(
            sum(
                rule.points
                for rule
                in PRIVACY_SCORE_RULES
            ),
            100,
        )

    def test_empty_report_scores_zero(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report()
            )
        )

        self.assertEqual(
            score.points,
            0,
        )

        self.assertEqual(
            score.percentage,
            0,
        )

        self.assertEqual(
            score.level,
            "LOW",
        )

    def test_gps_scores_40_points(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    "gps_coordinates"
                )
            )
        )

        self.assertEqual(
            score.points,
            40,
        )

        self.assertEqual(
            score.level,
            "MEDIUM",
        )

    def test_calculates_multiple_rules(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    "gps_coordinates",
                    "original_capture_date",
                    "device_model",
                    "owner_information",
                )
            )
        )

        self.assertEqual(
            score.points,
            70,
        )

        self.assertEqual(
            score.level,
            "HIGH",
        )

    def test_all_rules_score_100(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    *(
                        rule.code
                        for rule
                        in PRIVACY_SCORE_RULES
                    )
                )
            )
        )

        self.assertEqual(
            score.points,
            100,
        )

        self.assertEqual(
            score.percentage,
            100,
        )

        self.assertEqual(
            score.level,
            "HIGH",
        )

    def test_duplicate_findings_are_not_double_counted(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    "device_model",
                    "device_model",
                )
            )
        )

        self.assertEqual(
            score.points,
            10,
        )

    def test_unknown_finding_is_unscored(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    "gps_altitude",
                )
            )
        )

        self.assertEqual(
            score.points,
            0,
        )

        self.assertEqual(
            score.unscored_findings,
            (
                "gps_altitude",
            ),
        )

    def test_reports_unscored_privacy_findings(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    "gps_coordinates",
                    "gps_altitude",
                    "unique_identifier",
                    "editorial_location",
                )
            )
        )

        self.assertEqual(
            score.points,
            40,
        )

        self.assertEqual(
            score.unscored_findings,
            (
                "editorial_location",
                "gps_altitude",
                "unique_identifier",
            ),
        )

    def test_score_levels(
        self,
    ):

        low = (
            calculate_privacy_exposure_score(
                make_report(
                    "software",
                )
            )
        )

        medium = (
            calculate_privacy_exposure_score(
                make_report(
                    "serial_number",
                    "software",
                )
            )
        )

        high = (
            calculate_privacy_exposure_score(
                make_report(
                    "gps_coordinates",
                    "device_model",
                )
            )
        )

        self.assertEqual(
            low.level,
            "LOW",
        )

        self.assertEqual(
            medium.level,
            "MEDIUM",
        )

        self.assertEqual(
            high.level,
            "HIGH",
        )

    def test_builds_score_bar(
        self,
    ):

        self.assertEqual(
            build_score_bar(
                0
            ),
            "░░░░░░░░░░",
        )

        self.assertEqual(
            build_score_bar(
                70
            ),
            "███████░░░",
        )

        self.assertEqual(
            build_score_bar(
                100
            ),
            "██████████",
        )

    def test_formats_score_report(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    "gps_coordinates",
                    "device_model",
                )
            )
        )

        text = format_privacy_score(
            score
        )

        self.assertIn(
            "PRIVACY EXPOSURE SCORE",
            text,
        )

        self.assertIn(
            "HIGH",
            text,
        )

        self.assertIn(
            "50/100",
            text,
        )

        self.assertIn(
            "not a probability",
            text,
        )

    def test_formats_detailed_contributions(
        self,
    ):

        score = (
            calculate_privacy_exposure_score(
                make_report(
                    "gps_coordinates",
                    "device_model",
                    "gps_altitude",
                )
            )
        )

        text = (
            format_privacy_score_detailed(
                score
            )
        )

        self.assertIn(
            "+40",
            text,
        )

        self.assertIn(
            "GPS coordinates",
            text,
        )

        self.assertIn(
            "+10",
            text,
        )

        self.assertIn(
            "Device model",
            text,
        )

        self.assertIn(
            "UNSCORED FINDINGS",
            text,
        )

        self.assertIn(
            "gps_altitude",
            text,
        )


if __name__ == "__main__":
    unittest.main()
