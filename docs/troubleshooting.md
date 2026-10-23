# Troubleshooting

Common problems and checks. For settings, see [Configuration](configuration.md). For keys and commands, see [Usage](usage.md).

| Symptom | Check |
|---------|-------|
| The clock does not show in the sidebar | The `$tk_*` rows are missing from herdr's `config.toml`. Add them as in [Usage: Sidebar setup](usage.md#2-sidebar-setup), then run `herdr server reload-config`. |
| World clocks do not show | The zone name is wrong, or the system has no time zone data for it. The plugin skips zones it cannot load, so check the name with `world-list` and `world-add` (for example `Asia/Seoul`). On Windows, install the `tzdata` package with `python -m pip install tzdata` if IANA zones are unavailable. |
| Keys do nothing in the panel | The panel must have focus. Number keys may be taken by herdr when another pane is focused, so focus the panel pane first. |
| The language is not what you expect | The order is `HERDR_TIMEKIT_LANG`, then `"lang"` in `config.json`, then the OS language, then English. See [Configuration: Language](configuration.md#language). |
| Public holidays are missing or stale | Check `holiday_country` and inspect `host.log` in the plugin state directory for a failed Nager.Date refresh. A failed refresh keeps the previous cache; see [Configuration: Holiday theme](configuration.md#holiday-theme). When `host.log` passes 1 MiB it is moved to `host.log.1` (replacing the older copy), so at most two log files are kept. |
| The block seems stuck | Run `ensure` to restart the host. To stop everything, run `stop` first, then `ensure`. See [Usage: Commands](usage.md#commands). |
| The clock box looks misaligned | Emoji styles and some fonts use different widths. Try another `box_style` with the `b` key in the panel (see [Configuration: Clock box styles](configuration.md#clock-box-styles-box_style)). |

## Related

- [Usage](usage.md): sidebar setup, keys, commands, world clocks
- [Usage (한국어)](usage.ko.md)
- [Configuration](configuration.md): every `config.json` key
- [Development](development.md): project layout and how to add things
