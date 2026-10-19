# Configuration

herdr-timekit reads an optional `config.json`. If the file does not exist, the plugin uses its defaults.

> The keys below are planned and not implemented yet. Current code only reads the file and checks that it is a JSON object.

## File location

The plugin looks for the file in this order:

1. The path passed with `--config <path>`.
2. `$HERDR_PLUGIN_CONFIG_DIR/config.json`, when that environment variable is set.
3. The default location for your OS:
   - Windows: `%APPDATA%\herdr\plugins\config\herdr-timekit\config.json`
   - Linux and macOS: `$XDG_CONFIG_HOME/herdr/plugins/config/herdr-timekit/config.json` (defaults to `~/.config/...`)

## Example

```json
{
  "timezones": ["Asia/Seoul", "America/New_York", "Europe/London"],
  "default_timer_seconds": 1500
}
```

## Keys (planned)

| Key                     | Type            | Default | Description                              |
|-------------------------|-----------------|---------|------------------------------------------|
| `timezones`             | array of string | `[]`    | IANA time zone names shown by `world`    |
| `default_timer_seconds` | integer         | `1500`  | Length of a new timer, in seconds        |
| `now_style`             | string          | `"hm"`  | Format of the current time (see below)   |

`now_style` values:

| Value  | Example            |
|--------|--------------------|
| `hm`   | `14:41`            |
| `12h`  | `02:41 PM`         |
| `date` | `10/19 14:41`      |
| `week` | `Mon 14:41`        |
| `dateweek` | `10/19 Mon 14:41` |
| `compact` | `1441`          |
| `ymd` | `2026-12-25`       |
| `ymdhm` | `2026-12-25 14:41` |
| `kor12` | `오후 2:41`       |
| `full_kor` | `2026-10-19 오후 2시 41분` |
| `full_en` | `2026-10-19 PM 2:41` |

Seconds are never shown. An unknown value falls back to `hm`.

### Holiday theme

On a holiday, the sidebar time gets the holiday's emoji in front (for example `🌕 추석` style: `🌕 오후 2:52`). The detail screen shows the holiday name as well.

- `holiday_theme` (boolean, default `true`): set to `false` to turn it off.
- The holiday list is `holidays.json` in the plugin folder. Each entry has `date` (`YYYY-MM-DD`), `name`, and `emoji`. Edit it to change the emoji or add a holiday.
- The file covers 2026 only. Lunar holidays (설날, 부처님오신날, 추석) change every year, so add the next year's dates before then.

The file must contain a JSON object. Otherwise the command exits with an error.
