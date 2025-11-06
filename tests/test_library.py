import unittest
from datetime import datetime, timezone

from azul_runner.test_utils import FileManager

from azul_plugin_build_time_strings.library import (
    build_search_patterns,
    compare_times,
    extract_features,
    find_datetime_strings,
    round_hours,
)


class TestBuildTimeStrings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file_manager = FileManager()

    def test_build_search_patterns(self):
        """
        Ensure that we generate patterns which will be succesful in searching
        for strings representing datetimes in the correct range.
        """
        # Our patterns include hardcoded portions down to the day field, so we
        # expect two patterns back, as with a +- 12 hour window we'll need to
        # search for 20200420... and 20200421...
        target = datetime(2020, 4, 20, hour=16, minute=20, second=0)
        patterns = build_search_patterns(target)
        self.assertEqual(len(patterns), 2)
        self.assertTrue(b"20200420" in patterns[0])
        self.assertTrue(b"20200421" in patterns[1])

        # We actually want to search for a range slightly wider than 12 hours
        # to prevent the time taken to build the binary itself from pushing the
        # compile time further than 12 hours away. This would only be required
        # in the worst case scenario where a build begins very close to noon
        # the local timezone is UTC +12.
        target = datetime(2020, 4, 20, hour=12, minute=0, second=0)
        patterns = build_search_patterns(target)
        self.assertEqual(len(patterns), 3)
        self.assertTrue(b"20200419" in patterns[0])
        self.assertTrue(b"20200420" in patterns[1])
        self.assertTrue(b"20200421" in patterns[2])

        # Ensure that nothing strange happens across a month/year boundary.
        target = datetime(2019, 12, 31, hour=23, minute=0, second=0)
        patterns = build_search_patterns(target)
        self.assertEqual(len(patterns), 2)
        self.assertTrue(b"20191231" in patterns[0])
        self.assertTrue(b"20200101" in patterns[1])

    def test_find_datetime_strings(self):
        """
        find_datetime_strings() will locate candidate string patterns which
        might represent build times. Further functions will be used to validate
        these candidates, so we just need to check that it finds patterns which
        represent the right year/month/day values.
        """
        target = datetime(2020, 4, 20, hour=16, minute=20, second=0)

        # Generate a bunch of strings which we expect to detect when searching
        # based on the given target time.
        examples = []
        examples.append(b"\x00test_20200420162000_amd64.dll\x00")
        examples.append(b"\x00test_20200420162200_x86.dll\x00")
        examples.append(b"\x00test_20200420000000.dll\x00")
        examples.append(b"\x00test_20200420235959_final.dll\x00")
        examples.append(b"\x00test_2020042100000042.dll\x00")
        examples.append(b"\x00test_20200421235959,42_amd64.dll\x00")

        # We validate that we detected every pattern at offset 1, and that
        # we capture everything from "test_" to the ".dll".
        for example in examples:
            results = list(find_datetime_strings(example, target))
            expected = [(1, target, "test_20200420162000_amd64.dll")]
            self.assertEqual(results[0][0], 1)
            self.assertTrue(results[0][2].startswith("test_"))
            self.assertTrue(results[0][2].endswith(".dll"))

        # Generate some data containing string times out of range.
        invalid = []
        invalid.append(b"\x00test_20200419000000_amd64.dll\x00")
        invalid.append(b"\x00test_20200422000000_amd64.dll\x00")
        invalid.append(b"\x00test_20200520000000_amd64.dll\x00")
        invalid.append(b"\x00test_20180420000000_amd64.dll\x00")

        # Ensure that none of these were detected as candidates.
        for example in invalid:
            results = list(find_datetime_strings(example, target))
            self.assertEqual(len(results), 0)

    def test_round_hours(self):
        """
        Ensure that we correctly round fractions of hours to the nearest half
        hour.
        """
        examples = [
            (1.1, 1.0, 0.1),
            (1.5, 1.5, 0.0),
            (0.9, 1.0, -0.1),
            (-1.01, -1.0, -0.01),
            (-2.9997, -3.0, 0.0003),
            (11.26, 11.5, -0.24),
        ]
        for hours, expected_rounded, expected_remainder in examples:
            rounded, remainder = round_hours(hours)

            # Carefully compare floating point results with assertAlmostEqual()
            self.assertAlmostEqual(rounded, expected_rounded)
            self.assertAlmostEqual(remainder, expected_remainder)

    def test_compare_times(self):
        """
        Ensure that we correctly validate candidate times located by our patterns.
        """
        # To replicate the way this function is called in our package, the
        # target will be timezone aware, set to UTC time, and the candidate
        # will be timezone naive.
        target = datetime(2020, 4, 20, hour=16, minute=20, second=0, tzinfo=timezone.utc)

        # Generate some datetimes, which should all be considered near enough
        # to our target time.
        examples = [
            datetime(2020, 4, 20, hour=16, minute=20, second=5),
            datetime(2020, 4, 20, hour=16, minute=20, second=59),
            datetime(2020, 4, 20, hour=16, minute=21, second=0),
            datetime(2020, 4, 20, hour=16, minute=19, second=44),
            datetime(2020, 4, 20, hour=16, minute=19, second=0),
        ]

        for candidate in examples:
            result = compare_times(target, candidate)
            self.assertEqual(result, "UTC +0.0")

        # Generate some datetimes, which should also be considered near enough,
        # but only if interpreted in some other timezone.
        tz = [
            (datetime(2020, 4, 20, hour=15, minute=20, second=0), "UTC -1.0"),
            (datetime(2020, 4, 20, hour=17, minute=20, second=0), "UTC +1.0"),
            (datetime(2020, 4, 20, hour=4, minute=20, second=0), "UTC -12.0"),
            (datetime(2020, 4, 21, hour=4, minute=20, second=0), "UTC +12.0"),
            (datetime(2020, 4, 20, hour=11, minute=19, second=45), "UTC -5.0"),
            (datetime(2020, 4, 20, hour=19, minute=20, second=27), "UTC +3.0"),
        ]

        for candidate, expected in tz:
            result = compare_times(target, candidate)
            self.assertEqual(result, expected)

        # Generate some datetimes, which whie in the += 12 hour range, are not
        # sufficiently "near" the target time. We're configured to allow 60
        # seconds in either direction.
        bad = [
            datetime(2020, 4, 20, hour=16, minute=21, second=5),
            datetime(2020, 4, 20, hour=16, minute=18, second=59),
            datetime(2020, 4, 20, hour=17, minute=18, second=59),
            datetime(2020, 4, 20, hour=15, minute=18, second=59),
            datetime(2020, 4, 20, hour=4, minute=21, second=1),
        ]

        for candidate in bad:
            result = compare_times(target, candidate)
            self.assertEqual(result, None)

        # Ensure that nearby times that are outside the possible range which
        # could be caused by timezones are ignored. e.g. We don't want to let
        # patterns found by our regexes to generates timezones like
        # "UTC +14.0".
        bad = [
            datetime(2020, 4, 20, hour=0, minute=20, second=0),
            datetime(2020, 4, 20, hour=3, minute=20, second=0),
            datetime(2020, 4, 21, hour=5, minute=20, second=0),
            datetime(2020, 4, 21, hour=7, minute=20, second=0),
            datetime(2020, 4, 21, hour=23, minute=20, second=0),
        ]

        for candidate in bad:
            result = compare_times(target, candidate)
            self.assertEqual(result, None)

    def test_pe_error(self):
        """Test to verify pefile bug doesn't cause an error."""
        # PE file that causes an exception in build time strings.
        extract_features(
            self.file_manager.download_file_bytes("786be92057e56412091031b37a394e02192dad1404583556f511ca7db799c63e")
        )
        # If there isn't an exception it's good.
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
