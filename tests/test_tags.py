import unittest

from photometa.parsers.tags import (
    get_exif_tag_name,
    get_gps_tag_name,
    get_tiff_tag_name,
)


class TestTiffTags(unittest.TestCase):

    def test_known_tag(self):

        self.assertEqual(
            get_tiff_tag_name(0x010F),
            "Make",
        )

    def test_known_pointer_tag(self):

        self.assertEqual(
            get_tiff_tag_name(0x8769),
            "ExifIFDPointer",
        )

    def test_unknown_tag(self):

        self.assertEqual(
            get_tiff_tag_name(0xDEAD),
            "UnknownTag_DEAD",
        )


class TestExifIfdTags(unittest.TestCase):

    def test_exposure_time_tag(self):

        self.assertEqual(
            get_exif_tag_name(0x829A),
            "ExposureTime",
        )

    def test_datetime_original_tag(self):

        self.assertEqual(
            get_exif_tag_name(0x9003),
            "DateTimeOriginal",
        )

    def test_focal_length_tag(self):

        self.assertEqual(
            get_exif_tag_name(0x920A),
            "FocalLength",
        )

    def test_lens_model_tag(self):

        self.assertEqual(
            get_exif_tag_name(0xA434),
            "LensModel",
        )

    def test_image_unique_id_tag(self):

        self.assertEqual(
            get_exif_tag_name(
                0xA420
            ),
            "ImageUniqueID",
        )

    def test_camera_owner_name_tag(self):

        self.assertEqual(
            get_exif_tag_name(
                0xA430
            ),
            "CameraOwnerName",
        )

    def test_body_serial_number_tag(self):

        self.assertEqual(
            get_exif_tag_name(
                0xA431
            ),
            "BodySerialNumber",
        )

    def test_unknown_exif_tag(self):

        self.assertEqual(
            get_exif_tag_name(0xDEAD),
            "UnknownExifTag_DEAD",
        )
class TestGpsIfdTags(unittest.TestCase):

    def test_gps_latitude_tag(self):

        self.assertEqual(
            get_gps_tag_name(0x0002),
            "GPSLatitude",
        )

    def test_gps_longitude_tag(self):

        self.assertEqual(
            get_gps_tag_name(0x0004),
            "GPSLongitude",
        )

    def test_gps_date_stamp_tag(self):

        self.assertEqual(
            get_gps_tag_name(0x001D),
            "GPSDateStamp",
        )

    def test_unknown_gps_tag(self):

        self.assertEqual(
            get_gps_tag_name(0xDEAD),
            "UnknownGpsTag_DEAD",
        )

if __name__ == "__main__":
    unittest.main()
