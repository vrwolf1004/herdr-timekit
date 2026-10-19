# herdr-timekit

[**English**](README.md) | [한국어](README.ko.md)

A herdr plugin that shows the time, world clocks, a timer, and a counter in one block at the bottom of the sidebar, next to your AI coding agents.

## Dashboard design

Detail panel (opened in the timekit pane):

```
╭──────────────────────────────────────────────╮
│             🌸  herdr-timekit  🌸            │
├──────────────────────────────────────────────┤
│ 🕒 TIME                                      │
│   NOW       16:02                            │
│ 🌐 WORLD    Seoul          17:23 KST         │
│             New York       04:23 EDT         │
│             Tokyo          17:23 JST         │
│             Paris          10:23 CEST        │
├──────────────────────────────────────────────┤
│ ⏳ TIMER                                     │
│   VALUE     25:00           ready            │
│   PROGRESS  ████████████████                 │
├──────────────────────────────────────────────┤
│ 🔢 COUNTER                                   │
│   VALUE     0               stopped          │
├──────────────────────────────────────────────┤
│   [t] start/pause   [r] reset                │
│   [1-6] preset  10s 30s 1m 20m 30m 1h        │
│   [c] start/pause   [0] reset                │
│   [w] add zone   [x] remove last             │
│   [b] change clock design                    │
╰──────────────────────────────────────────────╯
```

Sidebar block (watch-style box, `box_style: emoji_tulip`, one of ten styles):

```
╔═════════════╗
║ 🌷 🌷 🌷 🌷 ║
║   PM 4:02   ║
║    10/19    ║
║ 🌷 🌷 🌷 🌷 ║
╚═════════════╝
```

The box shows the time and date. While the timer runs, it shows the timer value. While the counter runs, it shows the counter value. When the timer ends, the text blinks between `* done *` and `  done  `. Press `b` in the panel to change the design.

## Installation

```sh
herdr plugin install vrwolf1004/herdr-timekit
```

## Quick start

1. Install the plugin and add the sidebar rows (see [Usage](docs/usage.md#sidebar-setup)).
2. Click the timekit pane and press `t` to start the timer, or `c` to start the counter.
3. Press `w` to add a world clock by city name, for example `Seoul`.

## Requirements

- herdr 0.9.0 or later
- Windows, Linux, or macOS
- Python 3.9 or later (on Windows, also `python -m pip install tzdata`)

## Documentation

- [Usage](docs/usage.md): sidebar setup, keys, commands, world clocks
- [Configuration](docs/configuration.md): every `config.json` key
- [Development](docs/development.md): project layout and how to add things

## Support the project

If this project is useful to you, consider buying the developer a coffee.

[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
