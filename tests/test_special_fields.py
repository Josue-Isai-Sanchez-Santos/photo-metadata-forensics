import unittest

from photometa.interpretation.special_fields import (
    interpret_color_space,
    interpret_exposure_program,
    interpret_flash,
    interpret_gps_altitude_ref,
    interpret_metering_mode,
    interpret_orientation,
    interpret_scene_capture_type,
    interpret_special_field,
    interpret_white_balance,
)


class TestSpecialFieldInterpretation(
    unittest.TestCase
):

    def test_orientation(self):

        self.assertEqual(
            interpret_orientation(6),
            "Rotate 90° CW",
        )

    def test_flash(self):

        self.assertEqual(
            interpret_flash(16),
            "Off, did not fire",
        )

    def test_metering_mode(self):

        self.assertEqual(
            interpret_metering_mode(2),
            "Center-weighted average",
        )

    def test_exposure_program(self):

        self.assertEqual(
            interpret_exposure_program(1),
            "Manual",
        )

    def test_white_balance_auto(self):

        self.assertEqual(
            interpret_white_balance(0),
            "Auto",
        )

    def test_white_balance_manual(self):

        self.assertEqual(
            interpret_white_balance(1),
            "Manual",
        )

    def test_scene_capture_type(self):

        self.assertEqual(
            interpret_scene_capture_type(1),
            "Landscape",
        )

    def test_color_space(self):

        self.assertEqual(
            interpret_color_space(1),
            "sRGB",
        )

    def test_negative_ellipsoidal_altitude(
        self,
    ):

        self.assertEqual(
            interpret_gps_altitude_ref(1),
            "Negative ellipsoidal height",
        )

    def test_negative_sea_level_altitude(
        self,
    ):

        self.assertEqual(
            interpret_gps_altitude_ref(3),
            "Negative sea-level altitude",
        )

    def test_unknown_value_is_preserved(
        self,
    ):

        self.assertEqual(
            interpret_special_field(
                "Orientation",
                99,
            ),
            "Unknown (99)",
        )


if __name__ == "__main__":
    unittest.main()
