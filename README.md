# herdr-timekit

[한국어](README.ko.md) · English

A herdr plugin that shows the time, world clocks, a timer, and a counter in one block at the bottom of the sidebar, next to your AI coding agents.

- **Watch-style time box** in the sidebar, with a holiday emoji on public holidays and the timer shown while it runs.
- **Timer** with a countdown, pause, and reset.
- **Counter** that can count up over time, or be changed by hand.
- **World clocks** for any IANA time zone.
- **Detail panel** with keyboard controls, English or Korean labels.

## Installation

```sh
herdr plugin install vrwolf1004/herdr-timekit
```

## Requirements

- herdr 0.9.0 or later
- Windows, Linux, or macOS
- Python 3.9 or later
- On Windows, the `tzdata` package for world clocks: `python -m pip install tzdata`

## Sidebar setup

herdr only draws custom tokens that appear in your sidebar layout. Add the timekit rows to `[ui.sidebar.agents]` in herdr's `config.toml`, then run `herdr server reload-config`:

```toml
[ui.sidebar.agents]
rows = [
  # ...your other rows...
  [{ token = "$tk_box1", fg = "#8b949e" }],
  [{ token = "$tk_box2", fg = "#d2a8ff" }],
  [{ token = "$tk_box3", fg = "#e6edf3", bold = true }],
  [{ token = "$tk_box4", fg = "#7ee787" }],
  [{ token = "$tk_box5", fg = "#d2a8ff" }],
  [{ token = "$tk_box6", fg = "#8b949e" }],
]
```

herdr allows at most 16 sidebar rows, so keep the total within that limit.

## Keys (detail panel)

Click the timekit pane to focus it, then press:

| Key | Timer | Counter |
|-----|-------|---------|
| `t` | start / pause | |
| `r` | reset timer | |
| `c` | | start / pause (counts up once per second) |
| `+` / `-` | | change by one |
| `0` | | reset to 0 |

Korean keyboard input also works: `ㅅ` for `t`, `ㄱ` for `r`, `ㅊ` for `c`.

## Commands

Run from the plugin folder:

```sh
python -X utf8 src/timekit.py <command>
```

| Command | What it does |
|---------|--------------|
| `ensure` | Start the timekit block if it is not running |
| `stop` | Stop the block |
| `counter-inc` / `counter-dec` / `counter-reset` | Change the counter |
| `timer-start` / `timer-pause` / `timer-reset` | Control the timer |
| `world-add <zone>` | Add a time zone, e.g. `Asia/Seoul` |
| `world-remove <zone>` | Remove a time zone |
| `world-clear` | Remove all time zones |
| `world-list` | List the time zones |

`world-clear` and `world-list` are also available as herdr actions. Adding and removing need a name, so use the command line for those.

## Configuration

Settings live in `config.json` in the plugin config folder. See [Configuration](docs/configuration.md) for every key.

```json
{
  "lang": "en",
  "timezones": ["Asia/Seoul", "America/New_York"],
  "default_timer_seconds": 1500,
  "now_style": "hm",
  "box_style": "double_star",
  "holiday_theme": true
}
```

- `lang`: `en`, `ko`, `ru`, `fr`, `es`, `de`, or `ja`. Without it, the OS language is used, falling back to English.
- `box_style`: `double_star`, `square_dot`, `round_star`, `heavy_diamond`, `round_heart`, `emoji_flower`, `emoji_sparkle`, `emoji_person`, `emoji_tulip`, `emoji_rose`.
- `now_style`: `hm`, `12h`, `date`, `week`, `dateweek`, `compact`, `ymd`, `ymdhm`, `kor12`, `full_kor`, `full_en`.
- `holiday_theme`: adds a holiday emoji to the box. The holiday list is in `holidays.json`.

## Documentation

- [Configuration](docs/configuration.md)
- [Development](docs/development.md)

---

## Support the project

If this project is useful to you, consider buying the developer a coffee.

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
