# Development

## Layout

```
herdr-timekit/
├── README.md
├── docs/
│   ├── configuration.md
│   └── development.md
└── src/
    └── timekit.py      # command entry point
```

`herdr-plugin.toml` is not in the repository yet. It declares the plugin's actions and panes for herdr and is needed before the plugin can be installed.

## Running locally

```sh
python -X utf8 src/timekit.py --help
python -X utf8 src/timekit.py now
```

## Adding a command

1. Add a subparser in `build_parser()` in `src/timekit.py`.
2. Implement the command and dispatch to it from `main()`.
3. Declare a matching action in `herdr-plugin.toml`, with one entry per platform (`python` on Windows, `python3` on Linux and macOS), as herdr requires unique action IDs.
4. Document the command in `README.md`.

## Conventions

- Use Python 3 standard library only, unless a dependency is clearly needed.
- Run Python with `-X utf8` so output encoding is the same on every platform.
- Keep configuration parsing in `read_config()`, and report errors on stderr with exit code 1.
