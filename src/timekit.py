"""herdr-timekit: 현재 시간, 세계 시간, 카운터, 타이머를 herdr 사이드바 맨 아래 블록에 보여 준다.

동작 방식
  - 공용 "herdr-dock" workspace 에 pane 하나를 두고 가짜 agent(timekit)로 등록한다. dock 이 없으면 만들고,
    이미 있으면(다른 플러그인이 만든 경우) pane 을 나눠 들어간다.
    agents 패널은 spaces 순서로 정렬되므로 dock 을 항상 맨 뒤로 옮기면 블록이 맨 아래에 온다.
  - 그 pane 에서 host 루프가 돈다. 별도 백그라운드 프로세스를 두지 않으므로 pane 을 닫으면 같이 끝난다.
  - 값은 $tk_now, $tk_world, $tk_counter, $tk_timer 토큰으로 이 pane 에만 붙는다.
  - 카운터와 타이머는 state dir 의 파일로 저장한다. 액션은 파일만 바꾸고, host 가 매초 파일을 읽어 반영한다.

명령
  ensure          workspace 와 host 를 확인하고 없으면 띄운다 (startup / event hook)
  stop            host 를 멈추고 자기 pane 을 닫는다 (dock 이 비면 workspace 도 닫는다)
  host            timekit pane 안에서 도는 루프. 상세 화면 표시 + 사이드바 토큰 갱신
  counter-reset   카운터를 0으로
  timer-start     타이머 시작 (멈춘 상태면 이어서, 끝났거나 처음이면 기본 시간부터)
  timer-pause     타이머 일시정지
  timer-reset     타이머를 기본 시간으로 되돌림
"""

import argparse
import json
import os
import select
import sys
import time
import unicodedata
from datetime import datetime
import zoneinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import herdr_api
import i18n
from i18n import t

# 입력줄에서 쓰는 제어 문자
CR = chr(13)
LF = chr(10)
ESC = chr(27)
BS = chr(8)
DEL = chr(127)

PLUGIN_ID = "herdr-timekit"
SOURCE = f"plugin:{PLUGIN_ID}"
# 하단 고정 블록을 두는 공용 workspace. feedbag, stockpulse 와 같은 이름을 쓴다.
DOCK_LABEL = "herdr-dock"
AGENT_ID = "timekit"
DISPLAY_AGENT = "timekit"

TICK_SECONDS = 1             # 루프 한 바퀴 (heartbeat, 토큰 갱신)
HEARTBEAT_STALE_SECONDS = 10  # 이보다 오래 heartbeat 가 없으면 host 가 죽은 것으로 본다
TOKEN_TTL_MS = 15_000         # host 가 죽으면 토큰이 이 시간 뒤 사라진다
LAYOUT_EVERY_TICKS = 5        # 맨 아래 위치 확인, agent 재등록 주기
MAX_SOCKET_FAILURES = 10
DEFAULT_TIMER_SECONDS = 1500
# 키 1~6 으로 고르는 타이머 프리셋 (초)
TIMER_PRESETS = {"1": 10, "2": 30, "3": 60, "4": 1200, "5": 1800, "6": 3600}
# now_style 설정으로 고르는 현재 시간 표시 형식. 초는 표시하지 않는다. 모르는 값이면 기본(hm)을 쓴다.
# kor12 는 한국어 오전/오후 표기라 아래 now_text 에서 따로 만든다.
NOW_STYLES = {
    "hm": "%H:%M",
    "12h": "%I:%M %p",
    "date": "%m/%d %H:%M",
    "week": "%a %H:%M",
    "dateweek": "%m/%d %a %H:%M",
    "compact": "%H%M",
    "ymd": "%Y-%m-%d",
    "ymdhm": "%Y-%m-%d %H:%M",
    "kor12": None,
    "full_kor": None,
    "full_en": None,
}
DEFAULT_NOW_STYLE = "hm"
# herdr-sidebar 는 포커스된 탭마다 사이드바를 자동으로 띄운다. dock 에 뜨면 잠시 뒤 숨기기 키(b)를 보낸다.
SIDEBAR_TOKEN_PREFIX = "herdr-sidebar"
SIDEBAR_HIDE_KEY = "b"
SIDEBAR_HIDE_DELAY_SECONDS = 1
SIDEBAR_HIDE_RETRY_SECONDS = 5


# ---------------------------------------------------------------- 경로/설정


def default_state_dir():
    path = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if path:
        return path
    base = os.environ.get("LOCALAPPDATA") if herdr_api.IS_WINDOWS else os.path.expanduser("~/.local/state")
    return os.path.join(base or os.path.expanduser("~"), "herdr", "plugins", PLUGIN_ID)


def default_config_dir():
    path = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    if path:
        return path
    if herdr_api.IS_WINDOWS:
        base = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "herdr", "plugins", "config", PLUGIN_ID)


def load_config(config_dir):
    """config.json 을 읽는다. 파일이 없으면 빈 설정, 형식이 틀리면 ValueError."""
    path = os.path.join(config_dir, "config.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return loaded


def display_width(text):
    """터미널에서 차지하는 칸 수. 한글과 전각 문자는 두 칸으로 센다."""
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in text)


PANEL_INNER = 46
PROGRESS_WIDTH = 16
TIMER_STATUS_TEXT = {"idle": "ready", "running": "running", "paused": "paused", "done": "done"}


def pad_to(text, width):
    return text + " " * max(0, width - display_width(text))


def panel_row(text):
    """패널 한 줄. 양쪽 테두리 사이를 PANEL_INNER 칸으로 맞춘다."""
    return "│ " + pad_to(text, PANEL_INNER - 1) + "│"


def timer_bar(timer, now, default_seconds, width=PROGRESS_WIDTH):
    """남은 시간을 막대로 보여 준다. 기본 시간이 모두 남아 있으면 가득 찬다."""
    if timer["status"] == "running":
        remaining = max(0.0, timer["end_at"] - now)
    elif timer["status"] == "done":
        remaining = 0.0
    else:
        remaining = float(timer["remaining"])
    total = timer.get("total", default_seconds)
    fraction = min(1.0, remaining / total) if total else 0.0
    filled = round(fraction * width)
    return "█" * filled + "░" * (width - filled)


def center(text, width):
    space = width - display_width(text)
    left = space // 2
    return " " * left + text + " " * (space - left)


# box_style 설정으로 고르는 시계 테두리 모양. corners 는 왼위, 오른위, 왼아래, 오른아래 순서다.
BOX_STYLES = {
    "double_star": {"corners": "╔╗╚╝", "edge": "═", "side": "║", "ornament": "⭐"},
    "square_dot": {"corners": "┌┐└┘", "edge": "─", "side": "│", "ornament": "·"},
    "round_star": {"corners": "╭╮╰╯", "edge": "─", "side": "│", "ornament": "✦"},
    "heavy_diamond": {"corners": "┏┓┗┛", "edge": "━", "side": "┃", "ornament": "◆"},
    "round_heart": {"corners": "╭╮╰╯", "edge": "─", "side": "│", "ornament": "♥"},
    "emoji_flower": {"corners": "╔╗╚╝", "edge": "═", "side": "║", "ornament": "🌸"},
    "emoji_sparkle": {"corners": "╭╮╰╯", "edge": "─", "side": "│", "ornament": "✨"},
    "emoji_person": {"corners": "┌┐└┘", "edge": "─", "side": "│", "ornament": "🧍"},
    "emoji_tulip": {"corners": "╔╗╚╝", "edge": "═", "side": "║", "ornament": "🌷"},
    "emoji_rose": {"corners": "╭╮╰╯", "edge": "─", "side": "│", "ornament": "🌹"},
}
DEFAULT_BOX_STYLE = "double_star"


def watch_lines(moment, mark, box_style=DEFAULT_BOX_STYLE, timer_label=None, counter_label=None):
    """선택한 테두리 안에 장식, 시각, 날짜, 장식을 넣은 여섯 줄을 돌려준다. 휴일이면 날짜 앞에 이모지를 붙인다.
    timer_label 이 있으면 시각 자리에 타이머 값을, 날짜 자리에 TIMER 를 넣는다."""
    style = BOX_STYLES.get(box_style, BOX_STYLES[DEFAULT_BOX_STYLE])
    top_left, top_right, bottom_left, bottom_right = style["corners"]
    period = t("box.pm") if moment.hour >= 12 else t("box.am")
    time_text = f"{period} {moment.hour % 12 or 12}:{moment.minute:02d}"
    date_text = moment.strftime("%m/%d")
    if mark:
        date_text = f"{mark['emoji']} {date_text}"
    if counter_label:
        time_text = counter_label
        date_text = t("box.counter")
    elif timer_label:
        time_text = timer_label
        date_text = t("box.timer")
    width = max(display_width(time_text), display_width(date_text)) + 6
    ornament = style["ornament"]
    count = width // (display_width(ornament) + 1)
    stars = center(" ".join([ornament] * count), width)
    side = style["side"]
    return [
        top_left + style["edge"] * width + top_right,
        side + stars + side,
        side + center(time_text, width) + side,
        side + center(date_text, width) + side,
        side + stars + side,
        bottom_left + style["edge"] * width + bottom_right,
    ]


def load_holidays():
    """holidays.json 을 읽어 날짜(YYYY-MM-DD) → 휴일 항목 사전을 만든다. 파일이 없거나 고장나면 빈 사전이다."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "holidays.json")
    try:
        with open(path, encoding="utf-8") as file:
            entries = json.load(file).get("holidays", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return {}
    return {entry["date"]: entry for entry in entries if isinstance(entry, dict) and "date" in entry}


def holiday_mark(moment, config, holidays):
    """오늘이 휴일이면 그 항목을, 아니면 None 을 돌려준다. holiday_theme 을 false 로 두면 항상 None."""
    if not config.get("holiday_theme", True):
        return None
    return holidays.get(moment.strftime("%Y-%m-%d"))


def now_text(moment, config):
    """현재 시간 토큰. digital 형식 문자열."""
    style = config.get("now_style", DEFAULT_NOW_STYLE)
    if style not in NOW_STYLES:
        style = DEFAULT_NOW_STYLE
    if style == "kor12":
        period = "오전" if moment.hour < 12 else "오후"
        return f"{period} {moment.hour % 12 or 12}:{moment.minute:02d}"
    if style == "full_kor":
        period = "오전" if moment.hour < 12 else "오후"
        return f"{moment:%Y-%m-%d} {period} {moment.hour % 12 or 12}시 {moment.minute}분"
    if style == "full_en":
        period = "AM" if moment.hour < 12 else "PM"
        return f"{moment:%Y-%m-%d} {period} {moment.hour % 12 or 12}:{moment.minute:02d}"
    return moment.strftime(NOW_STYLES[style])


def timer_default_seconds(config):
    value = config.get("default_timer_seconds", DEFAULT_TIMER_SECONDS)
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return DEFAULT_TIMER_SECONDS


class State:
    """state dir 안의 작은 파일들. host 와 액션이 서로 다른 프로세스라 파일로 주고받는다."""

    def __init__(self, directory):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def path(self, name):
        return os.path.join(self.directory, name)

    def read(self, name):
        try:
            with open(self.path(name), encoding="utf-8") as file:
                return file.read().strip() or None
        except OSError:
            return None

    def write(self, name, value):
        with open(self.path(name), "w", encoding="utf-8") as file:
            file.write(value)

    def remove(self, name):
        try:
            os.remove(self.path(name))
        except OSError:
            pass

    def touch_heartbeat(self):
        self.write("heartbeat", str(time.time()))

    def host_alive(self):
        beat = self.read("heartbeat")
        try:
            return beat is not None and time.time() - float(beat) < HEARTBEAT_STALE_SECONDS
        except ValueError:
            return False

    def read_counter_state(self):
        """카운터 상태. value 는 started_at 시점의 값이고, started_at 이 None 이면 멈춰 있다."""
        try:
            loaded = json.loads(self.read("counter.json") or "null")
        except json.JSONDecodeError:
            loaded = None
        if not isinstance(loaded, dict) or not isinstance(loaded.get("value"), (int, float)):
            return {"value": 0, "started_at": None}
        return loaded

    def write_counter_state(self, counter):
        self.write("counter.json", json.dumps(counter))

    def read_timer(self, default_seconds):
        """타이머 상태. status 는 idle, running, paused, done 중 하나다."""
        try:
            timer = json.loads(self.read("timer.json") or "null")
        except json.JSONDecodeError:
            timer = None
        valid = (
            isinstance(timer, dict)
            and timer.get("status") in ("idle", "running", "paused", "done")
            and isinstance(timer.get("remaining"), (int, float))
        )
        if not valid:
            return {"status": "idle", "remaining": default_seconds, "end_at": None, "total": default_seconds}
        return timer

    def write_timer(self, timer):
        self.write("timer.json", json.dumps(timer))


# ---------------------------------------------------------------- 표시 값


def format_seconds(seconds):
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def timer_text(timer, now):
    """사이드바에 보일 타이머 값. 실행 중이면 ▶, 멈춤이면 ||, 끝났으면 done 을 붙인다."""
    status = timer["status"]
    if status == "running":
        remaining = max(0.0, timer["end_at"] - now)
        return f"▶ {format_seconds(remaining)}"
    if status == "done":
        return "done"
    if status == "paused":
        return f"|| {format_seconds(timer['remaining'])}"
    return format_seconds(timer["remaining"])


def world_text(timezones):
    """설정된 시간대마다 약어와 현재 시각을 한 줄로 이어 붙인다. 잘못된 이름은 ?? 로 표시한다."""
    parts = []
    now = datetime.now()
    for name in timezones:
        try:
            local = now.astimezone(ZoneInfo(name))
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            parts.append("??")
            continue
        parts.append(f"{local.tzname()} {local.strftime('%H:%M')}")
    return " ".join(parts) if parts else "-"


def world_lines(zones, limit=4):
    """세계 시간을 패널 한 줄씩 나눈다. 도시 이름, 시각, 약어 순서이며 limit 을 넘는 시간대는 개수만 적는다."""
    if not zones:
        return ["-"]
    now = datetime.now()
    rows = []
    for name in zones[:limit]:
        try:
            local = now.astimezone(ZoneInfo(name))
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            rows.append(f"{name} ??")
            continue
        city = name.split("/")[-1].replace("_", " ")
        rows.append(f"{city:<14} {local:%H:%M} {local.tzname()}")
    if len(zones) > limit:
        rows.append(f"+{len(zones) - limit} more")
    return rows


def expire_timer(timer, now):
    """실행 중인 타이머가 끝 시각을 지났으면 done 으로 바꾼다. 바뀌었으면 True 를 돌려준다."""
    if timer["status"] == "running" and now >= timer["end_at"]:
        timer.update({"status": "done", "remaining": 0, "end_at": None})
        return True
    return False


def timer_start(timer, now, default_seconds):
    if timer["status"] == "running":
        return timer
    remaining = timer["remaining"] if timer["status"] in ("idle", "paused") else default_seconds
    total = timer.get("total", remaining) if timer["status"] in ("idle", "paused") else remaining
    return {"status": "running", "remaining": remaining, "end_at": now + remaining, "total": total}


def counter_value(counter, now):
    """카운터 값. 실행 중이면 시작한 뒤 지난 초만큼 올라간다."""
    if counter["started_at"] is None:
        return int(counter["value"])
    return int(counter["value"] + (now - counter["started_at"]))


def counter_toggle(counter, now):
    """카운터를 시작하거나 멈춘다. 멈출 때 지금까지 올라간 값을 저장한다."""
    if counter["started_at"] is None:
        return {"value": counter["value"], "started_at": now}
    return {"value": counter_value(counter, now), "started_at": None}


def timer_pause(timer, now):
    if timer["status"] != "running":
        return timer
    remaining = max(0.0, timer["end_at"] - now)
    return {"status": "paused", "remaining": remaining, "end_at": None, "total": timer.get("total", remaining)}


def timer_reset(default_seconds):
    return {"status": "idle", "remaining": default_seconds, "end_at": None, "total": default_seconds}


# ---------------------------------------------------------------- workspace / pane


def find_workspace(workspaces):
    for workspace in workspaces:
        if workspace.get("label") == DOCK_LABEL:
            return workspace["workspace_id"]
    return None


def workspace_panes(workspace_id):
    panes = herdr_api.cli("pane", "list").get("panes", [])
    return [p for p in panes if p["workspace_id"] == workspace_id]


def is_sidebar(pane):
    return any(name.startswith(SIDEBAR_TOKEN_PREFIX) for name in (pane.get("tokens") or {}))


def pick_pane(panes, stored_pane, agent_panes):
    """dock 안에서 host 를 띄울 pane.

    기억해 둔 pane 이 살아 있으면 그것, 아니면 아무도 쓰지 않는 빈 pane(label·token·agent 없음).
    다른 플러그인 블록이나 herdr-sidebar pane 은 건드리지 않는다. 빈 pane 이 없으면 None.
    """
    ids = [p["pane_id"] for p in panes]
    if stored_pane in ids:
        return stored_pane
    free = [p["pane_id"] for p in panes
            if not p.get("label") and not p.get("tokens") and p["pane_id"] not in agent_panes]
    return free[0] if free else None


def ensure_workspace(state):
    """공용 dock workspace 와 그 안의 timekit pane 을 확보한다. dock 이 있으면 pane 을 하나 나눠 들어간다."""
    workspaces = herdr_api.cli("workspace", "list").get("workspaces", [])
    workspace_id = find_workspace(workspaces)
    if workspace_id is None:
        # cwd 를 git 저장소가 아닌 state dir 로 두어 branch/git 표시가 비게 한다.
        created = herdr_api.cli("workspace", "create", "--label", DOCK_LABEL, "--cwd", state.directory, "--no-focus")
        workspace_id = created["workspace"]["workspace_id"]
        state.remove("pane.id")
    state.write("workspace.id", workspace_id)
    panes = workspace_panes(workspace_id)
    agent_panes = {a["pane_id"] for a in herdr_api.cli("agent", "list").get("agents", [])}
    pane_id = pick_pane(panes, state.read("pane.id"), agent_panes)
    if pane_id is None:
        anchor = next((p["pane_id"] for p in panes if not is_sidebar(p)), None)
        if anchor is None:
            raise herdr_api.HerdrError(f"workspace {workspace_id} has no pane")
        split = herdr_api.cli("pane", "split", anchor, "--direction", "down", "--cwd", state.directory)
        pane_id = split["pane"]["pane_id"]
    state.write("pane.id", pane_id)
    return workspace_id, pane_id


def keep_at_bottom(workspace_id):
    workspaces = herdr_api.request("workspace.list", {}).get("workspaces", [])
    ids = [w["workspace_id"] for w in workspaces]
    if workspace_id not in ids:
        return False
    if ids[-1] != workspace_id:
        # insert_index 는 옮기기 전 목록 기준 "이 위치 앞에 넣기"다. 길이를 주면 맨 뒤로 간다.
        herdr_api.try_request("workspace.move", {"workspace_id": workspace_id, "insert_index": len(ids)})
    return True


# ---------------------------------------------------------------- ensure / stop


def host_command(state_dir, config_dir, pane_id):
    script = os.path.abspath(__file__)
    return [sys.executable, "-X", "utf8", script, "host", "--state", state_dir,
            "--config", config_dir, "--pane", pane_id]


def cmd_ensure(args):
    state = State(args.state)
    if state.host_alive():
        return 0
    # workspace 를 만들면 workspace.created hook 이 곧바로 ensure 를 한 번 더 부른다.
    # host 가 첫 heartbeat 를 쓰기 전이라 두 번째 호출이 같은 pane 에 명령을 또 입력하지 않도록 막는다.
    starting = state.read("starting")
    try:
        if starting is not None and time.time() - float(starting) < HEARTBEAT_STALE_SECONDS:
            return 0
    except ValueError:
        pass
    state.write("starting", str(time.time()))
    _, pane_id = ensure_workspace(state)
    state.remove("stop")
    herdr_api.cli("pane", "run", pane_id, *host_command(args.state, args.config, pane_id))
    return 0


def cmd_stop(args):
    state = State(args.state)
    state.write("stop", str(time.time()))
    deadline = time.time() + 3
    while state.host_alive() and time.time() < deadline:
        time.sleep(0.2)
    workspace_id = state.read("workspace.id")
    pane_id = state.read("pane.id")
    if workspace_id:
        # dock 은 다른 플러그인과 같이 쓴다. 자기 pane 만 닫고, 남은 게 herdr-sidebar 뿐이면 workspace 도 닫는다.
        others = [p for p in workspace_panes(workspace_id) if p["pane_id"] != pane_id and not is_sidebar(p)]
        if others:
            if pane_id:
                herdr_api.cli("pane", "close", pane_id, check=False)
        else:
            herdr_api.cli("workspace", "close", workspace_id, check=False)
    for name in ("workspace.id", "pane.id", "heartbeat"):
        state.remove(name)
    return 0


def cmd_counter(args):
    state = State(args.state)
    now = time.time()
    counter = state.read_counter_state()
    if args.action == "reset":
        counter = {"value": 0, "started_at": None}
    else:
        counter = counter_toggle(counter, now)
    state.write_counter_state(counter)
    return 0


def cmd_timer(args):
    state = State(args.state)
    default_seconds = timer_default_seconds(load_config_or_default(args.config))
    now = time.time()
    timer = state.read_timer(default_seconds)
    if args.action == "start":
        timer = timer_start(timer, now, default_seconds)
    elif args.action == "pause":
        timer = timer_pause(timer, now)
    else:
        timer = timer_reset(default_seconds)
    state.write_timer(timer)
    return 0


def load_config_or_default(config_dir):
    try:
        return load_config(config_dir)
    except ValueError as error:
        print(f"timekit: {error}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------- host


class Host:
    def __init__(self, args):
        self.state = State(args.state)
        self.config_dir = args.config
        self.pane_id = args.pane
        self.workspace_id = self.state.read("workspace.id")
        self.sidebar_seen = {}  # 사이드바 pane id → 처음 본 시각
        self.sidebar_sent = {}  # 사이드바 pane id → 마지막으로 숨기기 키를 보낸 시각
        self.socket_failures = 0
        self.config_error = None
        self.holidays = load_holidays()
        self.input_mode = None
        self.input_text = ""
        self.notice = ""
        self.timer_status = "idle"
        self.timer_label = ""
        self.registered_state = None
        self.mark = None
        self.counter_active = False
        self.counter_value_now = 0

    def settings(self):
        """매 틱 설정을 다시 읽는다. 고장난 파일이면 기본값을 쓰고 오류를 화면에 보여 준다."""
        try:
            config = load_config(self.config_dir)
            self.config_error = None
        except ValueError as error:
            config = {}
            self.config_error = str(error)
        return config

    def tokens(self, now, config):
        default_seconds = timer_default_seconds(config)
        timer = self.state.read_timer(default_seconds)
        if expire_timer(timer, now):
            self.state.write_timer(timer)
        self.timer_status = timer["status"]
        self.timer_label = timer_text(timer, now)
        self.timer_progress = timer_bar(timer, now, default_seconds)
        moment = datetime.fromtimestamp(now)
        mark = holiday_mark(moment, config, self.holidays)
        self.mark = mark
        current = now_text(moment, config)
        if mark:
            current = f"{mark['emoji']} {current}"
        tokens = {
            "tk_now": current,
            "tk_world": world_text(config.get("timezones", [])),
            "tk_counter": self.counter_text(now),
            "tk_timer": timer_text(timer, now),
        }
        timer_label = self.timer_label if self.timer_status != "idle" else None
        counter_label = f"# {self.counter_value_now}" if self.counter_active else None
        box = watch_lines(moment, mark, config.get("box_style", DEFAULT_BOX_STYLE), timer_label, counter_label)
        counter = self.state.read_counter_state()
        self.counter_active = counter["started_at"] is not None
        self.counter_value_now = counter_value(counter, now)
        self.world_lines = world_lines(config.get("timezones", []))
        for index, line in enumerate(box, 1):
            tokens[f"tk_box{index}"] = line
        return tokens

    def display_name(self):
        """돌고 있는 타이머 또는 카운터 값을 에이전트 이름에 붙인다. 둘 다 멈춰 있으면 이름만 쓴다."""
        return DISPLAY_AGENT

    def agent_state(self):
        """타이머가 돌고 있으면 working, 아니면 idle 로 보고한다."""
        return "working" if (self.timer_status == "running" or self.counter_active) else "idle"

    def report(self, tokens):
        ok = herdr_api.try_request("pane.report_metadata", {
            "pane_id": self.pane_id,
            "source": SOURCE,
            "display_agent": self.display_name(),
            "tokens": tokens,
            "ttl_ms": TOKEN_TTL_MS,
        })
        self.socket_failures = 0 if ok else self.socket_failures + 1

    def register_agent(self):
        self.registered_state = self.agent_state()
        herdr_api.try_request("pane.report_agent", {
            "pane_id": self.pane_id,
            "source": SOURCE,
            "agent": AGENT_ID,
            "state": self.registered_state,
        })
        if self.workspace_id:
            try:
                keep_at_bottom(self.workspace_id)
            except (herdr_api.HerdrError, ValueError):
                pass

    def hide_foreign_sidebars(self, now):
        if not self.workspace_id:
            return
        try:
            panes = herdr_api.request("pane.list", {"workspace_id": self.workspace_id}).get("panes", [])
        except (herdr_api.HerdrError, ValueError):
            return
        sidebars = {p["pane_id"] for p in panes if p["pane_id"] != self.pane_id and is_sidebar(p)}
        for pane_id in list(self.sidebar_seen):
            if pane_id not in sidebars:
                self.sidebar_seen.pop(pane_id, None)
                self.sidebar_sent.pop(pane_id, None)
        for pane_id in sidebars:
            first_seen = self.sidebar_seen.setdefault(pane_id, now)
            if now - first_seen < SIDEBAR_HIDE_DELAY_SECONDS:
                continue
            if now - self.sidebar_sent.get(pane_id, 0) < SIDEBAR_HIDE_RETRY_SECONDS:
                continue
            herdr_api.try_request("pane.send_keys", {"pane_id": pane_id, "keys": [SIDEBAR_HIDE_KEY]})
            self.sidebar_sent[pane_id] = now

    def handle_input(self, key, config):
        """세계 시간 입력줄에서 누른 키를 처리한다. Enter 는 추가, Esc 는 취소, Backspace 는 한 글자 지움."""
        if key in (CR, LF):
            self.input_mode = None
            self.add_zone(self.input_text.strip())
            self.input_text = ""
        elif key == ESC:
            self.input_mode = None
            self.input_text = ""
        elif key in (BS, DEL):
            self.input_text = self.input_text[:-1]
        elif key.isprintable() and len(self.input_text) < 64:
            self.input_text += key

    def add_zone(self, zone):
        if not zone:
            self.notice = t("cli.error", message=t("cli.world_needs_zone", action="add"))
            return
        resolved = resolve_zone(zone)
        if resolved is None:
            self.notice = t("cli.error", message=t("cli.unknown_zone", zone=zone))
            return
        zone = resolved
        try:
            config = load_config(self.config_dir)
        except ValueError as error:
            self.notice = t("cli.error", message=str(error))
            return
        zones = list(config.get("timezones", []))
        if zone in zones:
            self.notice = t("cli.error", message=t("cli.already", zone=zone))
            return
        config["timezones"] = zones + [zone]
        save_config(self.config_dir, config)
        self.notice = t("world.added", zone=zone)

    def remove_last_zone(self):
        try:
            config = load_config(self.config_dir)
        except ValueError as error:
            self.notice = t("cli.error", message=str(error))
            return
        zones = list(config.get("timezones", []))
        if not zones:
            self.notice = t("world.empty")
            return
        removed = zones.pop()
        config["timezones"] = zones
        save_config(self.config_dir, config)
        self.notice = t("world.removed", zone=removed)

    def change_box_style(self):
        """시계 박스 디자인을 다음 것으로 바꾸고 config.json 에 저장한다."""
        try:
            config = load_config(self.config_dir)
        except ValueError as error:
            self.notice = t("cli.error", message=str(error))
            return
        names = list(BOX_STYLES)
        current = config.get("box_style", DEFAULT_BOX_STYLE)
        index = names.index(current) if current in names else names.index(DEFAULT_BOX_STYLE)
        config["box_style"] = names[(index + 1) % len(names)]
        save_config(self.config_dir, config)
        self.notice = t("box.changed", style=config["box_style"])

    def counter_is_running(self):
        return self.state.read_counter_state()["started_at"] is not None

    def timer_is_running(self, now):
        timer = self.state.read_timer(DEFAULT_TIMER_SECONDS)
        return timer["status"] == "running" and now < timer["end_at"]

    def counter_text(self, now):
        """카운터 값. 실행 중이면 ▶, 멈춰 있으면 || 를 붙인다."""
        counter = self.state.read_counter_state()
        value = counter_value(counter, now)
        if counter["started_at"] is None:
            return f"|| {value}" if counter["value"] else str(value)
        return f"▶ {value}"

    def handle_key(self, key, config):
        """상세 화면에서 누른 키를 타이머(t, r)와 카운터(c, +, -, 0)에 반영한다."""
        now = time.time()
        default_seconds = timer_default_seconds(config)
        if self.input_mode:
            self.handle_input(key, config)
            return
        if key in TIMER_PRESETS:
            if self.timer_is_running(now):
                self.notice = t("exclusive.timer_running")
                return
            self.state.write_timer(timer_reset(TIMER_PRESETS[key]))
        elif key in ("t", "T", "ㅅ"):
            timer = self.state.read_timer(default_seconds)
            if timer["status"] != "running" and self.counter_is_running():
                self.notice = t("exclusive.counter_running")
                return
            if timer["status"] == "running":
                timer = timer_pause(timer, now)
            else:
                timer = timer_start(timer, now, default_seconds)
            self.state.write_timer(timer)
        elif key in ("r", "R", "ㄱ"):
            self.state.write_timer(timer_reset(default_seconds))
        elif key in ("c", "C", "ㅊ"):
            counter = self.state.read_counter_state()
            if counter["started_at"] is None and self.timer_is_running(now):
                self.notice = t("exclusive.timer_running")
                return
            self.state.write_counter_state(counter_toggle(counter, now))
        elif key in ("w", "W", "ㅈ"):
            self.input_mode = "world"
            self.input_text = ""
            self.notice = ""
        elif key in ("x", "X"):
            self.remove_last_zone()
        elif key in ("b", "B", "ㅠ"):
            self.change_box_style()
        elif key == "0":
            self.state.write_counter_state({"value": 0, "started_at": None})

    def draw(self, tokens):
        inner = PANEL_INNER
        world_rows = [panel_row("🌐 " + pad_to(t("row.world"), 9) + self.world_lines[0])]
        world_rows += [panel_row(" " * 12 + line) for line in self.world_lines[1:]]
        status = {"idle": "ready"}.get(self.timer_status, self.timer_status)
        timer_state = t("status." + status)
        counter_state = t("status.counting") if self.state.read_counter_state()["started_at"] is not None else t("status.stopped")
        lines = [
            "╭" + "─" * inner + "╮",
            panel_row(center("🌸  herdr-timekit  🌸", inner - 1)),
            "├" + "─" * inner + "┤",
            panel_row("🕒 " + t("section.time")),
            panel_row("  " + pad_to(t("row.now"), 10) + tokens["tk_now"]),
            *world_rows,
            "├" + "─" * inner + "┤",
            panel_row("⏳ " + t("section.timer")),
            panel_row("  " + pad_to(t("row.value"), 10) + pad_to(tokens["tk_timer"], 16) + timer_state),
            panel_row("  " + pad_to(t("row.progress"), 10) + self.timer_progress),
            "├" + "─" * inner + "┤",
            panel_row("🔢 " + t("section.counter")),
            panel_row("  " + pad_to(t("row.value"), 10) + pad_to(tokens["tk_counter"], 16) + counter_state),
            "├" + "─" * inner + "┤",
            panel_row("  " + t("keys.timer")),
            panel_row("  " + t("keys.preset")),
            panel_row("  " + t("keys.counter")),
            panel_row("  " + t("keys.world")),
            panel_row("  " + t("keys.box")),
            "╰" + "─" * inner + "╯",
        ]
        if self.mark:
            name = self.mark["name"] if i18n.language() == "ko" else self.mark.get("name_en", self.mark["name"])
            lines.append(f"  {t('holiday.label')}  {self.mark['emoji']} {name}")
        if self.input_mode:
            lines.append(f"  {t('world.prompt', value=self.input_text)}_")
        if self.notice:
            lines.append(f"  {self.notice}")
        if self.config_error:
            lines += ["", f"  {t('config.error')}: {self.config_error}"]
        sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(lines) + "\n")
        sys.stdout.flush()

    def run(self):
        sys.stdout.write("\033[?25l")  # 커서 숨김
        self.state.remove("starting")
        restore_terminal = enter_key_mode()
        tick = 0
        try:
            while self.state.read("stop") is None and self.socket_failures < MAX_SOCKET_FAILURES:
                self.state.touch_heartbeat()
                now = time.time()
                config = self.settings()
                tokens = self.tokens(now, config)
                if tick % LAYOUT_EVERY_TICKS == 0 or self.agent_state() != self.registered_state:
                    self.register_agent()
                self.hide_foreign_sidebars(now)
                self.report(tokens)
                self.draw(tokens)
                tick += 1
                deadline = now + TICK_SECONDS
                while time.time() < deadline:
                    key = read_key()
                    if key:
                        self.handle_key(key, config)
                        self.draw(self.tokens(time.time(), config))
                    else:
                        time.sleep(0.1)
        finally:
            restore_terminal()
            sys.stdout.write("\033[?25h")
            herdr_api.try_request("pane.release_agent", {"pane_id": self.pane_id, "source": SOURCE, "agent": AGENT_ID})
            self.state.remove("heartbeat")
            self.state.remove("stop")
        return 0


def enter_key_mode():
    """키를 한 글자씩 바로 받을 수 있게 터미널을 바꾸고, 원래대로 돌리는 함수를 돌려준다."""
    if herdr_api.IS_WINDOWS:
        return lambda: None
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    except (OSError, ValueError, ImportError):
        return lambda: None
    return lambda: termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def read_key():
    """기다리지 않고 눌린 키 한 글자를 돌려준다. 없으면 빈 문자열이다."""
    if herdr_api.IS_WINDOWS:
        import msvcrt
        return msvcrt.getwch() if msvcrt.kbhit() else ""
    try:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        return os.read(sys.stdin.fileno(), 1).decode("utf-8", "ignore") if ready else ""
    except (OSError, ValueError):
        return ""


def resolve_zone(name):
    """도시 이름(Seoul, new york)이나 시간대 이름(asia/seoul)을 IANA 시간대 이름으로 바꾼다. 대소문자는 구분하지 않는다. 찾지 못하면 None."""
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


def save_config(config_dir, config):
    os.makedirs(config_dir, exist_ok=True)
    with open(os.path.join(config_dir, "config.json"), "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
        file.write("\n")


def cmd_world(args):
    """세계 시간 목록(config.json 의 timezones)을 추가, 삭제, 비우기, 보기를 한다."""
    try:
        config = load_config(args.config)
    except ValueError as error:
        print(f"timekit: {error}", file=sys.stderr)
        return 1
    zones = list(config.get("timezones", []))
    if args.action == "list":
        print("\n".join(zones) if zones else t("cli.none"))
        return 0
    if args.action == "clear":
        zones = []
    else:
        if not args.value:
            print(t("cli.error", message=t("cli.world_needs_zone", action=args.action)), file=sys.stderr)
            return 1
        if args.action == "add":
            resolved = resolve_zone(args.value)
            if resolved is None:
                print(t("cli.error", message=t("cli.unknown_zone", zone=args.value)), file=sys.stderr)
                return 1
            args.value = resolved
            if args.value in zones:
                print(t("cli.error", message=t("cli.already", zone=args.value)))
                return 0
            zones.append(args.value)
        else:
            if args.value not in zones:
                print(t("cli.error", message=t("cli.not_in_list", zone=args.value)), file=sys.stderr)
                return 1
            zones.remove(args.value)
    config["timezones"] = zones
    save_config(args.config, config)
    print("\n".join(zones) if zones else t("cli.none"))
    return 0


def cmd_host(args):
    try:
        return Host(args).run()
    except KeyboardInterrupt:
        return 0


# ---------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(prog=PLUGIN_ID)
    parser.add_argument("command", choices=[
        "ensure", "stop", "host", "counter-reset",
        "timer-start", "timer-pause", "timer-reset",
        "world-add", "world-remove", "world-clear", "world-list",
    ])
    parser.add_argument("value", nargs="?", help="time zone name, e.g. Asia/Seoul (world-add, world-remove)")
    parser.add_argument("--state", default=default_state_dir())
    parser.add_argument("--config", default=default_config_dir())
    parser.add_argument("--pane", default=os.environ.get("HERDR_PANE_ID"))
    args = parser.parse_args(argv)
    os.environ.setdefault("HERDR_PLUGIN_CONFIG_DIR", args.config)
    i18n.set_language(i18n.detect())
    args.action = args.command.split("-", 1)[1] if "-" in args.command else None
    commands = {
        "ensure": cmd_ensure,
        "stop": cmd_stop,
        "host": cmd_host,
        "counter-reset": cmd_counter,
        "timer-start": cmd_timer,
        "timer-pause": cmd_timer,
        "timer-reset": cmd_timer,
        "world-add": cmd_world,
        "world-remove": cmd_world,
        "world-clear": cmd_world,
        "world-list": cmd_world,
    }
    try:
        return commands[args.command](args)
    except herdr_api.HerdrError as error:
        print(f"timekit: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
