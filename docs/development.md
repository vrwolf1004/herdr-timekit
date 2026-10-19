# Development

## Layout

```
herdr-timekit/
├── README.md, README.ko.md     short overview (English, Korean)
├── herdr-plugin.toml           herdr manifest: startup, events, actions
├── holidays.json               public holidays (date, name, name_en, emoji)
├── docs/
│   ├── usage.md, usage.ko.md   keys, sidebar setup, commands
│   ├── configuration.md        every config.json key
│   ├── development.md          this file
│   └── todo.md                 improvement list
└── src/
    ├── timekit.py              entry point: host loop, panel, commands
    ├── herdr_api.py            herdr CLI and socket helpers
    ├── i18n.py                 language choice and t(key, **values)
    └── locales/<language>.json translated strings (en, ko, ru, fr, es, de, ja)
```

## Running locally

```sh
python -X utf8 src/timekit.py --help
python -X utf8 src/timekit.py world-list
```

The host runs inside herdr's timekit pane. To restart it after a code change:

```sh
python -X utf8 src/timekit.py stop
python -X utf8 src/timekit.py ensure
```

## Adding a command

1. Add the name to `choices` in `main()` in `src/timekit.py`, and map it to a function in `commands`.
2. Implement the function. Use `t("key")` for every user-facing message.
3. If herdr should run it, add an action in `herdr-plugin.toml`, one entry for Windows (`python`, id ending in `-windows`) and one for Linux/macOS (`python3`). herdr requires unique action ids and cannot pass arguments to actions.
4. Document it in `docs/usage.md` and `docs/usage.ko.md`.

## Adding or changing a string

Every language file in `src/locales/` must have the same keys. Add the key to all seven files, then use it with `t("key")`. Keep panel labels short: the panel is 48 columns wide, and Japanese and Korean characters take two columns.

## Adding a clock box style

Add an entry to `BOX_STYLES` in `src/timekit.py` with `corners` (top-left, top-right, bottom-left, bottom-right), `edge`, `side`, and `ornament`. Then document it in `docs/configuration.md`. The style is selectable from the panel with `b`.

## Holidays

Edit `holidays.json`. Dates are `YYYY-MM-DD`. Keep `name` (Korean) and `name_en` (English) filled in. Lunar holidays need a new entry each year.

## Conventions

- Use the Python standard library only, unless a dependency is clearly needed (currently `tzdata` on Windows).
- Run Python with `-X utf8` so output encoding is the same on every platform.
- Keep the panel within 48 columns, and check line widths with `display_width()` after changing layout.
- Report errors on stderr and return exit code 1 from commands.
