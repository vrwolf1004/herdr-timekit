# Configuration

herdr-timekit reads an optional `config.json`. If the file does not exist, the plugin uses its defaults. The file must contain a JSON object.

## File location

The plugin looks for the file in this order:

1. The folder passed with `--config <folder>`.
2. `$HERDR_PLUGIN_CONFIG_DIR/config.json`, when that environment variable is set.
3. The default location for your OS:
   - Windows: `%APPDATA%\herdr\plugins\config\herdr-timekit\config.json`
   - Linux and macOS: `$XDG_CONFIG_HOME/herdr/plugins/config/herdr-timekit/config.json` (defaults to `~/.config/...`)

## Example

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

## Keys

| Key                     | Type            | Default       | Description                                             |
|-------------------------|-----------------|---------------|---------------------------------------------------------|
| `lang`                  | string          | OS language   | Language of the panel, box labels, and messages (see below) |
| `timezones`             | array of string | `[]`          | Time zones shown as world clocks (see [Usage](usage.md#world-clocks)) |
| `default_timer_seconds` | integer         | `1500`        | Length of a new timer, in seconds                       |
| `now_style`             | string          | `"hm"`        | Format of the time in the sidebar and panel (see below) |
| `box_style`             | string          | `"double_star"` | Frame of the sidebar clock box (see below)            |
| `holiday_theme`         | boolean         | `true`        | Show a holiday emoji and name on public holidays        |

## Clock box styles (`box_style`)

Press `b` in the panel to step through the styles; the choice is saved here.

| Value            | Frame          | Ornament row |
|------------------|----------------|--------------|
| `double_star`    | `╔═╗ ║ ╚═╝`    | ⭐           |
| `square_dot`     | `┌─┐ │ └─┘`    | `·`          |
| `round_star`     | `╭─╮ │ ╰─╯`    | `✦`          |
| `heavy_diamond`  | `┏━┓ ┃ ┗━┛`    | `◆`          |
| `round_heart`    | `╭─╮ │ ╰─╯`    | `♥`          |
| `emoji_flower`   | `╔═╗ ║ ╚═╝`    | 🌸           |
| `emoji_sparkle`  | `╭─╮ │ ╰─╯`    | ✨           |
| `emoji_person`   | `┌─┐ │ └─┘`    | 🧍           |
| `emoji_tulip`    | `╔═╗ ║ ╚═╝`    | 🌷           |
| `emoji_rose`     | `╭─╮ │ ╰─╯`    | 🌹           |

The box shows the time and date. While the timer runs it shows the timer value and `TIMER`.

## Sidebar time format (`now_style`)

| Value      | Example                    |
|------------|----------------------------|
| `hm`       | `14:41`                    |
| `12h`      | `02:41 PM`                 |
| `date`     | `10/19 14:41`              |
| `week`     | `Mon 14:41`                |
| `dateweek` | `10/19 Mon 14:41`          |
| `compact`  | `1441`                     |
| `ymd`      | `2026-12-25`               |
| `ymdhm`    | `2026-12-25 14:41`         |
| `kor12`    | `오후 2:41`                |
| `full_kor` | `2026-10-19 오후 2시 41분` |
| `full_en`  | `2026-10-19 PM 2:41`       |

Seconds are never shown. An unknown value falls back to `hm`.

## Holiday theme

On a holiday, the sidebar time gets the holiday's emoji in front, and the panel shows the holiday name.

- `holiday_theme` turns this on or off.
- The holiday list is `holidays.json` in the plugin folder. Each entry has `date` (`YYYY-MM-DD`), `name` (Korean), `name_en` (English), and `emoji`. Edit it to change emoji or names, or to add holidays.
- The file covers 2026 only. Lunar holidays (설날, 부처님오신날, 추석) change every year, so add the next year's dates before then.

## Language

`lang` sets the language of the panel, the sidebar box labels, and the command messages.

Supported: `en`, `ko`, `ru`, `fr`, `es`, `de`, `ja`.

The language is chosen in this order:

1. The `HERDR_TIMEKIT_LANG` environment variable
2. `"lang"` in `config.json`
3. The OS language (Windows UI language, or `LC_ALL` / `LC_MESSAGES` / `LANG`)
4. English (`en`)

Missing translations fall back to English. Translations live in `src/locales/<language>.json`. Holiday names use `name` for Korean and `name_en` for English; other languages show the English name.
