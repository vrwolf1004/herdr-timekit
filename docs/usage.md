# Usage

[**English**](usage.md) | [한국어](usage.ko.md)

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

herdr allows at most 16 sidebar rows in total, so keep the count within that limit.

## Detail panel keys

Click the timekit pane to focus it, then press:

| Key | Timer | Counter | World clocks |
|-----|-------|---------|--------------|
| `t` | start / pause | | |
| `r` | reset timer | | |
| `c` | | start / pause (counts up once per second) | |
| `+` / `-` | | change by one | |
| `0` | | reset to 0 | |
| `w` | | | add a time zone (type the name, Enter to add, Esc to cancel) |
| `x` | | | remove the last time zone |
| `b` | | | change the clock design (cycles through the box styles, saved to `box_style`) |

Korean keyboard input also works: `ㅅ` for `t`, `ㄱ` for `r`, `ㅈ` for `w`, `ㅊ` for `c`.

## World clocks

Add time zones from the panel with `w`, or from the command line:

```sh
python -X utf8 src/timekit.py world-add Seoul
python -X utf8 src/timekit.py world-remove Asia/Seoul
python -X utf8 src/timekit.py world-list
python -X utf8 src/timekit.py world-clear
```

Enter a city name such as `Seoul` or `New York`, or an IANA time zone name such as `America/New_York`. City names are matched against the IANA list. Letter case does not matter (`seoul`, `Seoul`, and `SEOUL` all work). On Windows, install `tzdata` for world clocks to work.

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
| `world-add <zone>` | Add a time zone |
| `world-remove <zone>` | Remove a time zone |
| `world-clear` | Remove all time zones |
| `world-list` | List the time zones |

`world-clear` and `world-list` are also herdr actions. Adding and removing need a name, so they are command-line only (and available in the panel with `w` and `x`).

## Language

The panel, box labels, and messages follow the language setting. See [Configuration: Language](configuration.md#language).
