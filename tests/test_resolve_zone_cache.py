import os
import sys
import unittest
import zoneinfo
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
os.environ.setdefault("HERDR_TIMEKIT_LANG", "en")

import timekit  # noqa: E402

INPUTS = [
    "Seoul", "new york", "NEW YORK", "  Paris  ", "asia/seoul", "ASIA/SEOUL", "Asia/Seoul",
    "europe/paris", "America/New_York", "new_york", "utc", "UTC", "Nowhere", "nosuchcity", "", "   ",
]


def reference_resolve_zone(name):
    """개선 전 구현을 그대로 옮긴 것. 호출할 때마다 목록을 정렬한다. 결과 비교용."""
    key = name.strip().replace(" ", "_").lower()
    if not key:
        return None
    zones = sorted(zoneinfo.available_timezones())
    by_name = {zone.lower(): zone for zone in zones}
    if key in by_name:
        return by_name[key]
    for zone in zones:
        if "/" in zone and zone.split("/")[-1].lower() == key:
            return zone
    return None


class ResolveZoneSameResultTest(unittest.TestCase):
    def setUp(self):
        timekit._zone_index_cache = None

    def tearDown(self):
        timekit._zone_index_cache = None

    def test_same_results_as_before_for_representative_inputs(self):
        for name in INPUTS:
            with self.subTest(name=name):
                timekit._zone_index_cache = None
                self.assertEqual(timekit.resolve_zone(name), reference_resolve_zone(name))

    def test_city_and_zone_names_resolve_as_before(self):
        self.assertEqual(timekit.resolve_zone("Seoul"), "Asia/Seoul")
        self.assertEqual(timekit.resolve_zone("new york"), "America/New_York")
        self.assertEqual(timekit.resolve_zone("asia/seoul"), "Asia/Seoul")
        self.assertIsNone(timekit.resolve_zone("nosuchcity"))
        self.assertIsNone(timekit.resolve_zone("   "))


class ResolveZoneCacheTest(unittest.TestCase):
    def setUp(self):
        timekit._zone_index_cache = None
        self.real = zoneinfo.available_timezones
        patch = mock.patch.object(zoneinfo, "available_timezones", side_effect=self.real)
        self.counter = patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(setattr, timekit, "_zone_index_cache", None)

    def test_second_lookup_does_not_read_the_zone_list_again(self):
        timekit.resolve_zone("Seoul")
        timekit.resolve_zone("Paris")
        timekit.resolve_zone("asia/seoul")
        timekit.resolve_zone("nowhere")
        self.assertEqual(self.counter.call_count, 1)

    def test_empty_input_does_not_build_the_index(self):
        self.assertIsNone(timekit.resolve_zone("   "))
        self.assertEqual(self.counter.call_count, 0)


if __name__ == "__main__":
    unittest.main()
