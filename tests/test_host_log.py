import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import timekit  # noqa: E402

LINE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (.*)$")


class HostLogTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.state = timekit.State(self.folder.name)
        self.log = Path(self.folder.name, "host.log")
        self.rotated = Path(self.folder.name, "host.log.1")

    def test_small_log_is_appended_without_rotation(self):
        self.log.write_text("first\n", encoding="utf-8")
        self.state.append_log("second")
        self.assertFalse(self.rotated.exists())
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "first")
        self.assertEqual(LINE.match(lines[1]).group(1), "second")

    def test_a_log_exactly_at_the_limit_is_not_rotated(self):
        self.log.write_bytes(b"x" * timekit.HOST_LOG_MAX_BYTES)
        self.state.append_log("next")
        self.assertFalse(self.rotated.exists())

    def test_a_log_over_the_limit_moves_to_host_log_1_and_a_new_host_log_is_written(self):
        old = b"x" * (timekit.HOST_LOG_MAX_BYTES + 1)
        self.log.write_bytes(old)
        self.state.append_log("fresh")
        self.assertEqual(self.rotated.read_bytes(), old)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(LINE.match(lines[0]).group(1), "fresh")

    def test_an_older_host_log_1_is_overwritten(self):
        self.rotated.write_text("older rotation\n", encoding="utf-8")
        self.log.write_bytes(b"y" * (timekit.HOST_LOG_MAX_BYTES + 1))
        self.state.append_log("fresh")
        self.assertNotIn(b"older rotation", self.rotated.read_bytes())
        self.assertEqual(self.rotated.read_bytes()[:1], b"y")
        self.assertEqual(sorted(p.name for p in Path(self.folder.name).iterdir()), ["host.log", "host.log.1"])

    def test_write_failure_does_not_raise(self):
        self.log.write_bytes(b"x" * (timekit.HOST_LOG_MAX_BYTES + 1))
        with mock.patch.object(timekit.os, "replace", side_effect=OSError("disk full")):
            self.state.append_log("fresh")  # 예외 없이 끝나야 한다
        with mock.patch.object(timekit, "open", side_effect=OSError("no access"), create=True):
            self.state.append_log("fresh")


if __name__ == "__main__":
    unittest.main()
