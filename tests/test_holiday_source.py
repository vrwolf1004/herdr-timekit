import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import holiday_source as hs  # noqa: E402


def fake_year(year, country):
    return {f"{year}-01-01": {"date": f"{year}-01-01", "emoji": "🎉", "name": "새해", "name_en": "New Year's Day"}}


class CountryTest(unittest.TestCase):
    def test_languages_map_to_countries(self):
        self.assertEqual(hs.country_for_language("ko"), "KR")
        self.assertEqual(hs.country_for_language("ja"), "JP")
        self.assertEqual(hs.country_for_language("xx"), "US")

    def test_emoji_rules(self):
        self.assertEqual(hs.emoji_for("Lunar New Year", "설날"), "🧧")
        self.assertEqual(hs.emoji_for("Chuseok", "추석"), "🌕")
        self.assertEqual(hs.emoji_for("Labour Day", "노동절"), hs.DEFAULT_EMOJI)


class ParseTest(unittest.TestCase):
    def test_keeps_local_and_english_names(self):
        entries = hs.parse_year([{"date": "2027-01-01", "localName": "새해", "name": "New Year's Day"}])
        self.assertEqual(entries["2027-01-01"]["name"], "새해")
        self.assertEqual(entries["2027-01-01"]["name_en"], "New Year's Day")

    def test_skips_items_without_a_date(self):
        self.assertEqual(hs.parse_year([{"name": "x"}, "junk"]), {})


class FetchTest(unittest.TestCase):
    def test_network_failure_gives_none(self):
        def broken(url, timeout):
            raise OSError("offline")
        self.assertIsNone(hs.fetch_year(2027, "KR", opener=broken))

    def test_valid_response_is_parsed(self):
        body = json.dumps([{"date": "2027-02-06", "localName": "설날", "name": "Lunar New Year"}]).encode()

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        entries = hs.fetch_year(2027, "KR", opener=lambda url, timeout: Response(body))
        self.assertEqual(entries["2027-02-06"]["emoji"], "🧧")


class RefreshRuleTest(unittest.TestCase):
    def cache(self, start, country="KR"):
        return {"country": country, "start": start, "entries": {}}

    def test_no_cache_needs_refresh(self):
        self.assertTrue(hs.needs_refresh(None, "KR", 2026))

    def test_first_four_years_keep_the_window(self):
        for year in (2026, 2027, 2028, 2029):
            self.assertFalse(hs.needs_refresh(self.cache(2026), "KR", year), year)

    def test_fifth_year_refreshes(self):
        self.assertTrue(hs.needs_refresh(self.cache(2026), "KR", 2030))

    def test_country_change_refreshes(self):
        self.assertTrue(hs.needs_refresh(self.cache(2026, "KR"), "JP", 2026))

    def test_year_before_window_refreshes(self):
        self.assertTrue(hs.needs_refresh(self.cache(2026), "KR", 2025))

    def test_refresh_fetches_five_years_from_now(self):
        requested = []

        def fetch(year, country):
            requested.append(year)
            return fake_year(year, country)

        data = hs.refresh("KR", 2029, fetch)
        self.assertEqual(requested, [2029, 2030, 2031, 2032, 2033])
        self.assertEqual(data["start"], 2029)
        self.assertEqual(len(data["entries"]), 5)

    def test_one_failed_year_gives_none(self):
        self.assertIsNone(hs.refresh("KR", 2026, lambda year, country: None))


class HolidaysForTest(unittest.TestCase):
    def test_fetches_once_then_uses_the_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def fetch(year, country):
                calls.append(year)
                return fake_year(year, country)

            first = hs.holidays_for(directory, "KR", 2026, fetch=fetch)
            second = hs.holidays_for(directory, "KR", 2027, fetch=fetch)
        self.assertEqual(len(calls), 5)  # 두 번째 호출은 받지 않는다
        self.assertIn("2026-01-01", first)
        self.assertIn("2027-01-01", second)

    def test_failure_keeps_the_old_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            hs.holidays_for(directory, "KR", 2026, fetch=lambda y, c: fake_year(y, c))
            kept = hs.holidays_for(directory, "KR", 2029, fetch=lambda y, c: None)
        self.assertIn("2026-01-01", kept)

    def test_bundled_entries_are_used_only_for_korea(self):
        bundled = {"2099-05-05": {"date": "2099-05-05", "emoji": "🎊", "name": "번들", "name_en": "Bundled"}}
        with tempfile.TemporaryDirectory() as directory:
            kr = hs.holidays_for(directory, "KR", 2026, bundled=bundled, fetch=lambda y, c: fake_year(y, c))
        with tempfile.TemporaryDirectory() as directory:
            us = hs.holidays_for(directory, "US", 2026, bundled=bundled, fetch=lambda y, c: fake_year(y, c))
        self.assertIn("2099-05-05", kr)
        self.assertNotIn("2099-05-05", us)


if __name__ == "__main__":
    unittest.main()
