# herdr-timekit

A herdr plugin that puts time-related tools in one place: the current time, world clocks, counters, and timers. Keep them visible while you work with your AI coding agents.

> Status: early development. The command entry point and project layout are in place; the features below are not implemented yet.

## Features (planned)

- **Current time**: your local time, always visible.
- **World clock**: check the time in multiple cities or time zones at once.
- **Counter**: a simple counter you can increment, decrement, and reset.
- **Timer**: start, pause, and reset countdown or stopwatch timers.

## Installation

```sh
herdr plugin install vrwolf1004/herdr-timekit
```

## Requirements

- herdr 0.9.0 or later
- Windows, Linux, or macOS
- Python 3

## Usage

The plugin entry point is `src/timekit.py`:

```sh
python -X utf8 src/timekit.py <command>
```

| Command   | Description                          |
|-----------|--------------------------------------|
| `now`     | Print the current local time         |
| `world`   | Print the configured world clocks    |
| `counter` | Show the counter                     |
| `timer`   | Show the timer                       |
| `panel`   | Open the timekit panel               |

Pass `--config <path>` to use a specific configuration file.

## Documentation

- [Configuration](docs/configuration.md)
- [Development](docs/development.md)
