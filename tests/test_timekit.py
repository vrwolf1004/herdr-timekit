import json
import os
from datetime import datetime
import sys
import tempfile
import time
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock
from contextlib import redirect_stderr

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
os.environ.setdefault("HERDR_TIMEKIT_LANG", "en")

import timekit  # noqa: E402


class PaneAliveTest(unittest.TestCase):
    def test_missing_pane_is_not_alive(self):
        from unittest import mock
        with mock.patch.object(timekit.herdr_api, "cli", return_value=None):
            self.assertFalse(timekit.pane_alive("wN:p1"))

    def test_existing_pane_is_alive(self):
        from unittest import mock
        with mock.patch.object(timekit.herdr_api, "cli", return_value={"pane": {"pane_id": "wN:p1"}}):
            self.assertTrue(timekit.pane_alive("wN:p1"))

    def test_no_pane_id_is_not_alive(self):
        self.assertFalse(timekit.pane_alive(None))


class CounterTest(unittest.TestCase):
    def test_stopped_counter_keeps_its_value(self):
        self.assertEqual(timekit.counter_value({"value": 7, "started_at": None}, 100.0), 7)

    def test_running_counter_grows_by_elapsed_seconds(self):
        self.assertEqual(timekit.counter_value({"value": 7, "started_at": 100.0}, 105.0), 12)

    def test_toggle_stops_and_saves_the_value(self):
        running = timekit.counter_toggle({"value": 0, "started_at": None}, 100.0)
        stopped = timekit.counter_toggle(running, 110.0)
        self.assertEqual(stopped, {"value": 10, "started_at": None})


class TimerTest(unittest.TestCase):
    def test_start_then_expire_at_end_time(self):
        timer = timekit.timer_start({"status": "idle", "remaining": 60, "total": 60}, 100.0, 60)
        self.assertEqual(timer["end_at"], 160.0)
        self.assertFalse(timekit.expire_timer(timer, 159.0))
        self.assertTrue(timekit.expire_timer(timer, 160.0))
        self.assertEqual(timer["status"], "done")

    def test_pause_keeps_the_remaining_time_and_resume_continues(self):
        timer = timekit.timer_start({"status": "idle", "remaining": 60, "total": 60}, 100.0, 60)
        paused = timekit.timer_pause(timer, 130.0)
        self.assertEqual(paused["status"], "paused")
        self.assertEqual(paused["remaining"], 30.0)
        resumed = timekit.timer_start(paused, 200.0, 60)
        self.assertEqual(resumed["end_at"], 230.0)

    def test_reset_returns_to_default(self):
        self.assertEqual(timekit.timer_reset(90)["remaining"], 90)


class StateWriteTest(unittest.TestCase):
    def test_write_replaces_value_without_leftover_temp_file(self):
        with tempfile.TemporaryDirectory() as directory:
            state = timekit.State(directory)
            state.write("counter.json", "1")
            state.write("counter.json", "2")
            self.assertEqual(state.read("counter.json"), "2")
            self.assertFalse(os.path.exists(state.path("counter.json") + ".tmp"))

    def test_failed_write_keeps_previous_value(self):
        with tempfile.TemporaryDirectory() as directory:
            state = timekit.State(directory)
            state.write("timer.json", "old")
            with mock.patch.object(timekit.os, "replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    state.write("timer.json", "new")
            self.assertEqual(state.read("timer.json"), "old")


class HolidayTest(unittest.TestCase):
    def load(self, entries):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "holidays.json")
            Path(path).write_text(json.dumps({"holidays": entries}), encoding="utf-8")
            err = StringIO()
            with redirect_stderr(err):
                holidays = timekit.load_holidays(path)
        return holidays, err.getvalue()

    def test_valid_entry_is_kept(self):
        holidays, warnings = self.load([{"date": "2027-01-01", "emoji": "🎉", "name": "New Year"}])
        self.assertIn("2027-01-01", holidays)
        self.assertEqual(warnings, "")

    def test_bad_entries_are_skipped_with_a_warning(self):
        holidays, warnings = self.load([
            {"date": "2027-02-30", "emoji": "x", "name": "no such day"},
            {"date": "2027-03-01", "emoji": 5, "name": "bad emoji"},
            "not an object",
        ])
        self.assertEqual(holidays, {})
        self.assertEqual(warnings.count("skipped entry"), 3)

    def test_missing_file_gives_empty_mapping(self):
        self.assertEqual(timekit.load_holidays(os.path.join(tempfile.gettempdir(), "no-such-holidays.json")), {})


class CounterOnBoxTest(unittest.TestCase):
    """같은 틱에서 바뀐 카운터가 박스에 그대로 보여야 한다 (예전에는 한 틱 늦었다)."""

    def test_box_shows_the_counter_value_of_this_tick(self):
        with tempfile.TemporaryDirectory() as directory:
            state = timekit.State(directory)
            now = time.time()
            state.write_counter_state({"value": 0, "started_at": now - 5})
            host = timekit.Host.__new__(timekit.Host)
            host.state = state
            host.holidays = {}
            host.counter_active = False
            host.counter_value_now = None
            host.holiday_key = ("US", datetime.fromtimestamp(now).year)  # 네트워크 갱신을 건너뛴다
            tokens = host.tokens(now, {})
        self.assertEqual(host.counter_value_now, 5)
        self.assertIn("# 5", "\n".join(tokens[f"tk_box{i}"] for i in range(1, 20) if f"tk_box{i}" in tokens))


class BoxWidthTest(unittest.TestCase):
    def test_all_box_lines_have_the_same_width(self):
        import datetime
        moment = datetime.datetime(2027, 3, 15, 10, 30)
        for style in ("square_dot", "round_star"):
            lines = timekit.watch_lines(moment, None, style, timer_label="00:10", counter_label="# 3")
            widths = {timekit.display_width(timekit.ANSI_RE.sub("", line)) if hasattr(timekit, "ANSI_RE")
                      else timekit.display_width(line) for line in lines}
            self.assertEqual(len(widths), 1, style)


class LocaleKeysTest(unittest.TestCase):
    def test_every_locale_has_the_same_keys_as_english(self):
        locales = SRC / "locales"
        english = set(json.loads((locales / "en.json").read_text(encoding="utf-8")))
        for path in sorted(locales.glob("*.json")):
            keys = set(json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual(keys, english, path.name)


class PlaceholderTest(unittest.TestCase):
    def test_every_locale_uses_the_same_placeholders_as_english(self):
        import re
        pattern = re.compile(r"\{[a-zA-Z_]+\}")
        locales = SRC / "locales"
        english = json.loads((locales / "en.json").read_text(encoding="utf-8"))
        for path in sorted(locales.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for key, text in data.items():
                if key in english:
                    self.assertEqual(set(pattern.findall(text)), set(pattern.findall(english[key])),
                                     f"{path.name}: {key}")


if __name__ == "__main__":
    unittest.main()
