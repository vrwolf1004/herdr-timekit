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
  counter-inc     카운터 +1
  counter-dec     카운터 -1
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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import herdr_api
import i18n
from i18n import t

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
    fraction = min(1.0, remaining / default_seconds) if default_seconds else 0.0
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


def watch_lines(moment, mark, box_style=DEFAULT_BOX_STYLE, timer_label=None):
    """선택한 테두리 안에 장식, 시각, 날짜, 장식을 넣은 여섯 줄을 돌려준다. 휴일이면 날짜 앞에 이모지를 붙인다.
    timer_label 이 있으면 시각 자리에 타이머 값을, 날짜 자리에 TIMER 를 넣는다."""
    style = BOX_STYLES.get(box_style, BOX_STYLES[DEFAULT_BOX_STYLE])
    top_left, top_right, bottom_left, bottom_right = style["corners"]
    period = t("box.pm") if moment.hour >= 12 else t("box.am")
    time_text = f"{period} {moment.hour % 12 or 12}:{moment.minute:02d}"
    date_text = moment.strftime("%m/%d")
    if mark:
        date_text = f"{mark['emoji']} {date_text}"
    if timer_label:
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
            return {"status": "idle", "remaining": default_seconds, "end_at": None}
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


def expire_timer(timer, now):
    """실행 중인 타이머가 끝 시각을 지났으면 done 으로 바꾼다. 바뀌었으면 True 를 돌려준다."""
    if timer["status"] == "running" and now >= timer["end_at"]:
        timer.update({"status": "done", "remaining": 0, "end_at": None})
        return True
    return False


def timer_start(timer, now, default_seconds):
    if timer["status"] == "running":
        return timer
    remaining = timer["remaining"] if timer["status"] == "paused" else default_seconds
    return {"status": "running", "remaining": remaining, "end_at": now + remaining}


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


def counter_adjust(counter, now, delta):
    """값을 delta 만큼 바꾼다. 실행 중이면 실행 상태를 그대로 둔다."""
    value = counter_value(counter, now) + delta
    return {"value": value, "started_at": now if counter["started_at"] is not None else None}


def timer_pause(timer, now):
    if timer["status"] != "running":
        return timer
    remaining = max(0.0, timer["end_at"] - now)
    return {"status": "paused", "remaining": remaining, "end_at": None}


def timer_reset(default_seconds):
    return {"status": "idle", "remaining": default_seconds, "end_at": None}


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
    elif args.action == "start":
        counter = counter_toggle(counter, now)
    else:
        counter = counter_adjust(counter, now, 1 if args.action == "inc" else -1)
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
        self.timer_status = "idle"
        self.timer_label = ""
        self.registered_state = None
        self.mark = None

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
        box = watch_lines(moment, mark, config.get("box_style", DEFAULT_BOX_STYLE), timer_label)
        for index, line in enumerate(box, 1):
            tokens[f"tk_box{index}"] = line
        return tokens

    def display_name(self):
        """타이머가 돌거나 멈춰 있거나 끝났으면 에이전트 이름에 타이머 값을 붙인다."""
        if self.timer_status == "idle":
            return DISPLAY_AGENT
        return f"{DISPLAY_AGENT} {self.timer_label}"

    def agent_state(self):
        """타이머가 돌고 있으면 working, 아니면 idle 로 보고한다."""
        return "working" if self.timer_status == "running" else "idle"

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
        if key in ("t", "T", "ㅅ"):
            timer = self.state.read_timer(default_seconds)
            if timer["status"] == "running":
                timer = timer_pause(timer, now)
            else:
                timer = timer_start(timer, now, default_seconds)
            self.state.write_timer(timer)
        elif key in ("r", "R", "ㄱ"):
            self.state.write_timer(timer_reset(default_seconds))
        elif key in ("c", "C", "ㅊ"):
            self.state.write_counter_state(counter_toggle(self.state.read_counter_state(), now))
        elif key in ("+", "="):
            self.state.write_counter_state(counter_adjust(self.state.read_counter_state(), now, 1))
        elif key == "-":
            self.state.write_counter_state(counter_adjust(self.state.read_counter_state(), now, -1))
        elif key == "0":
            self.state.write_counter_state({"value": 0, "started_at": None})

    def draw(self, tokens):
        inner = PANEL_INNER
        status = {"idle": "ready"}.get(self.timer_status, self.timer_status)
        timer_state = t("status." + status)
        counter_state = t("status.counting") if self.state.read_counter_state()["started_at"] is not None else t("status.stopped")
        lines = [
            "╭" + "─" * inner + "╮",
            panel_row(center("🌸  herdr-timekit  🌸", inner - 1)),
            "├" + "─" * inner + "┤",
            panel_row("🕒 " + t("section.time")),
            panel_row("  " + pad_to(t("row.now"), 10) + tokens["tk_now"]),
            panel_row("🌐 " + pad_to(t("row.world"), 9) + tokens["tk_world"]),
            "├" + "─" * inner + "┤",
            panel_row("⏳ " + t("section.timer")),
            panel_row("  " + pad_to(t("row.value"), 10) + pad_to(tokens["tk_timer"], 16) + timer_state),
            panel_row("  " + pad_to(t("row.progress"), 10) + self.timer_progress),
            "├" + "─" * inner + "┤",
            panel_row("🔢 " + t("section.counter")),
            panel_row("  " + pad_to(t("row.value"), 10) + pad_to(tokens["tk_counter"], 16) + counter_state),
            "├" + "─" * inner + "┤",
            panel_row("  " + t("keys.timer")),
            panel_row("  " + t("keys.counter")),
            "╰" + "─" * inner + "╯",
        ]
        if self.mark:
            name = self.mark["name"] if i18n.language() == "ko" else self.mark.get("name_en", self.mark["name"])
            lines.append(f"  {t('holiday.label')}  {self.mark['emoji']} {name}")
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
            try:
                ZoneInfo(args.value)
            except (ZoneInfoNotFoundError, ValueError):
                print(t("cli.error", message=t("cli.unknown_zone", zone=args.value)), file=sys.stderr)
                return 1
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
        "ensure", "stop", "host", "counter-inc", "counter-dec", "counter-reset",
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
        "counter-inc": cmd_counter,
        "counter-dec": cmd_counter,
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
