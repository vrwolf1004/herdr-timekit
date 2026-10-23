import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
os.environ.setdefault("HERDR_TIMEKIT_LANG", "en")

import timekit  # noqa: E402


def world_args(config_dir, action, value=None):
    return types.SimpleNamespace(config=config_dir, action=action, value=value)


def box_host(config_dir):
    """Host 전체를 만들지 않고, change_box_style 이 쓰는 값만 가진 흉내 객체."""
    return types.SimpleNamespace(config_dir=config_dir, notice=None)


class AtomicSaveTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.dir = self.folder.name
        self.path = Path(self.dir, "config.json")

    def test_failure_before_replace_keeps_the_old_file_and_leaves_no_temp(self):
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul"]})
        before = self.path.read_text(encoding="utf-8")
        with mock.patch.object(timekit.os, "replace", side_effect=OSError("disk gone")):
            with self.assertRaises(OSError):
                timekit.save_config(self.dir, {"timezones": []})
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)
        self.assertEqual([name for name in os.listdir(self.dir) if name.endswith(".tmp")], [])

    def test_saved_text_has_the_same_format_as_before(self):
        config = {"timezones": ["Asia/Seoul"], "box_style": "round"}
        timekit.save_config(self.dir, config)
        expected = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(self.path.read_text(encoding="utf-8"), expected)
        self.assertEqual(timekit.load_config(self.dir), config)

    def test_missing_folder_is_created(self):
        nested = os.path.join(self.dir, "nested")
        timekit.save_config(nested, {"timezones": []})
        self.assertEqual(timekit.load_config(nested), {"timezones": []})


class UpdateConfigTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.dir = self.folder.name
        self.path = Path(self.dir, "config.json")
        # cmd_world 가 내는 안내 줄은 테스트 출력에 섞지 않는다
        for stream in ("stdout", "stderr"):
            patch = mock.patch.object(sys, stream, new_callable=io.StringIO)
            patch.start()
            self.addCleanup(patch.stop)

    def test_alternating_zone_and_style_changes_both_remain(self):
        names = list(timekit.BOX_STYLES)
        timekit.cmd_world(world_args(self.dir, "add", "Asia/Seoul"))
        timekit.Host.change_box_style(box_host(self.dir))
        timekit.cmd_world(world_args(self.dir, "add", "Europe/Paris"))
        timekit.Host.change_box_style(box_host(self.dir))
        config = timekit.load_config(self.dir)
        self.assertEqual(config["timezones"], ["Asia/Seoul", "Europe/Paris"])
        default = names.index(timekit.DEFAULT_BOX_STYLE)
        self.assertEqual(config["box_style"], names[(default + 2) % len(names)])

    def test_each_change_uses_the_latest_file_not_a_stale_copy(self):
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul"], "box_style": timekit.DEFAULT_BOX_STYLE})
        # 다른 명령이 시간대를 바꾼 뒤에 스타일만 바꾼다. 스타일 저장이 시간대를 되돌리면 안 된다.
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul", "Europe/Paris"],
                                       "box_style": timekit.DEFAULT_BOX_STYLE})
        timekit.Host.change_box_style(box_host(self.dir))
        config = timekit.load_config(self.dir)
        self.assertEqual(config["timezones"], ["Asia/Seoul", "Europe/Paris"])
        self.assertNotEqual(config["box_style"], timekit.DEFAULT_BOX_STYLE)

    def test_returning_false_writes_nothing(self):
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul"]})
        before = self.path.read_text(encoding="utf-8")
        self.assertFalse(timekit.update_config(self.dir, lambda config: False))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_adding_an_existing_zone_is_reported_and_not_saved(self):
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul"]})
        before = self.path.read_text(encoding="utf-8")
        self.assertEqual(timekit.cmd_world(world_args(self.dir, "add", "Asia/Seoul")), 0)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_removing_a_zone_not_in_the_list_is_an_error(self):
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul"]})
        self.assertEqual(timekit.cmd_world(world_args(self.dir, "remove", "Europe/Paris")), 1)
        self.assertEqual(timekit.load_config(self.dir), {"timezones": ["Asia/Seoul"]})

    def test_failed_write_during_a_world_change_keeps_the_old_file(self):
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul"], "box_style": timekit.DEFAULT_BOX_STYLE})
        before = self.path.read_text(encoding="utf-8")
        with mock.patch.object(timekit.os, "replace", side_effect=OSError("disk gone")):
            with self.assertRaises(OSError):
                timekit.cmd_world(world_args(self.dir, "add", "Europe/Paris"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_clear_and_remove_last_keep_other_keys(self):
        timekit.save_config(self.dir, {"timezones": ["Asia/Seoul", "Europe/Paris"], "box_style": "round"})
        host = box_host(self.dir)
        host.notice = None
        timekit.Host.remove_last_zone(host)
        self.assertEqual(timekit.load_config(self.dir), {"timezones": ["Asia/Seoul"], "box_style": "round"})
        self.assertEqual(timekit.cmd_world(world_args(self.dir, "clear")), 0)
        self.assertEqual(timekit.load_config(self.dir), {"timezones": [], "box_style": "round"})


if __name__ == "__main__":
    unittest.main()
