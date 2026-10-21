# Architecture

`herdr-plugin.toml` starts the timekit host on plugin startup and registers its controls as herdr actions. The host runs in its own pane in the shared `herdr-dock` workspace, reports agent state, and renders clock, timer, counter, and world-clock data as sidebar tokens and a focused pane.

Configuration is read from `config.json`; persistent timer and counter state and the holiday cache live in the plugin state directory. The counter is calculated from the current tick before rendering, so the sidebar token and clock box use the same value and a running counter advances once per second.

Holiday data comes from the Nager.Date public API. `holiday_source.py` requests a five-calendar-year window and saves it in `holidays-cache.json`; it refreshes when the country changes or the year reaches `start + 4` (the fifth calendar year in the cached window). Holiday refresh work runs on a daemon thread. A failed refresh leaves the previous cache in place and the host writes the failure to `host.log`. Korean entries from the bundled `holidays.json` supplement fetched entries and take precedence for matching dates.

See [Configuration](configuration.md) for settings and cache behavior, [Usage](usage.md) for controls, and [Development](development.md) for source layout and test commands.
