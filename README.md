# herdr-timekit

[**English**](README.md) | [한국어](README.ko.md)

UI languages: English · Korean · Russian · French · Spanish · German · Japanese

Show the current time, world clocks, a timer, and a counter in one block at the bottom of herdr's sidebar.

## Dashboard design

Agents sidebar:

```text
┌────── TIME ──────┐
│     13:45:08     │
│   Sat, Mar 08    │
│  Seoul  13:45    │
│  Tokyo  13:45    │
└──────────────────┘
```

Timekit pane:

```text
╭──────────────────────────────────────────────╮
│               🐺  herdr-timekit  🌕          │
├──────────────────────────────────────────────┤
│  TIME                                         │
│  13:45:08  Saturday, March 8                  │
│                                              │
│  WORLD CLOCKS                                │
│  Seoul       13:45   Asia/Seoul              │
│  New York    23:45   America/New_York        │
├──────────────────────────────────────────────┤
│  TIMER                 COUNTER               │
│  20:00                 1,234                 │
│  [t] start/pause       [c] start/pause       │
│  [r] reset             [0] reset             │
├──────────────────────────────────────────────┤
│  [1-6] presets  [w] add clock  [b] style     │
╰──────────────────────────────────────────────╯
```

## Installation

```sh
herdr plugin install vrwolf1004/herdr-timekit
```

## Actions

| Action | What it does |
| --- | --- |
| `start` / `stop` | Show or hide the time block |
| `counter-reset` | Reset the counter |
| `timer-start` / `timer-pause` / `timer-reset` | Control or reset the timer |
| `world-list` / `world-clear` | List or clear world clocks |

On Windows, append `-windows` to each action ID. See the [usage guide](docs/usage.md) for sidebar setup, pane controls, presets, and world clocks.

## Requirements

- herdr 0.9.0 or later
- Windows, Linux, or macOS
- Python 3.9 or later; on Windows, also run `python -m pip install tzdata`

## Documentation

- [Usage (English)](docs/usage.md)
- [사용법 (한국어)](docs/usage.ko.md)
- [Configuration](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development](docs/development.md)

## Support the project

If this project is useful to you, consider buying the developer a coffee.

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
