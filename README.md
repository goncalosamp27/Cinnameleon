# Cinnameleon

> A lightweight appearance profile manager for Linux Mint Cinnamon that adapts your desktop to the current wallpaper.

Cinnameleon watches the active wallpaper and applies the matching appearance profile automatically. Each profile can define GTK themes, window borders, icons, cursors, fonts, and separate Dark and Light variants.

The application runs in the Cinnamon system tray and reacts to wallpaper changes through `Gio.Settings`, without polling.

> **Project status:** Alpha. Cinnameleon is functional and usable, but it is still being tested across clean Linux Mint installations and different theme configurations.

---

## Features

- Wallpaper-based appearance profiles
- Automatic, event-driven wallpaper detection
- Dark and Light variants for each profile
- Native Cinnamon tray integration through `XAppStatusIcon`
- Manual profile selection from the tray
- Dark Mode toggle from the tray
- Automatic configuration reload
- Validation of installed themes and fonts
- Safety snapshots before appearance changes
- Restore support
- Local desktop launcher
- Optional session autostart
- Standalone user installation
- No background polling

---

## Supported environment

Cinnameleon is currently designed and tested for:

- Linux Mint Cinnamon
- Cinnamon desktop environment
- GTK 3
- Python 3.12
- XApp

Other Cinnamon-based distributions may work, but they are not officially tested yet.

---

## How it works

Cinnameleon uses the wallpaper as the identifier for the active profile.

For example:

```yaml
profiles:
  - id: ocean
    name: Ocean
    wallpaper: ocean.jpg

  - id: forest
    name: Forest
    wallpaper: forest.jpg
```

When the desktop wallpaper becomes `ocean.jpg`, Cinnameleon resolves the `ocean` profile and applies its appearance settings.

The selected global mode determines whether the profile uses its Dark or Light variants.

```yaml
gtk_theme:
  dark: Mint-Y-Dark
  light: Mint-Y
```

Cinnameleon listens to Cinnamon's wallpaper setting through `Gio.Settings`. It does not repeatedly scan the system or poll for changes.

---

## Requirements

Install the required system packages:

```bash
sudo apt update

sudo apt install \
  python3 \
  python3-venv \
  python3-gi \
  python3-yaml \
  gir1.2-gtk-3.0 \
  gir1.2-xapp-1.0 \
  fontconfig \
  desktop-file-utils
```

The installer checks the required Python, GTK, Gio, XApp, and PyYAML dependencies before completing the installation.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/goncalosamp27/Cinnameleon.git
cd Cinnameleon
```

Run the installer:

```bash
./scripts/install.sh
```

The installer:

1. Creates a private Python environment.
2. Installs the Cinnameleon Python package.
3. Installs the application and tray icons.
4. Creates the Cinnamon application menu entry.
5. Enables session autostart.
6. Preserves an existing user configuration.
7. Creates a starter configuration when possible.

Cinnameleon is installed under:

```text
~/.local/share/cinnameleon/
```

The executable is located at:

```text
~/.local/share/cinnameleon/venv/bin/cinnameleon
```

### Install without autostart

```bash
./scripts/install.sh --no-autostart
```

### Show installer options

```bash
./scripts/install.sh --help
```

---

## Starting Cinnameleon

After installation, open the Cinnamon application menu and search for:

```text
Cinnameleon
```

Cinnameleon starts directly in the system tray.

When autostart is enabled, it also starts automatically when the Cinnamon session begins.

To start it manually from a terminal:

```bash
~/.local/share/cinnameleon/venv/bin/cinnameleon run
```

Verbose logging:

```bash
~/.local/share/cinnameleon/venv/bin/cinnameleon run --verbose
```

---

## Tray menu

The tray menu provides quick access to:

```text
Cinnameleon

Current profile
✓ Ocean

Theme profile  ▶
    ● Ocean
    ○ Forest

☑ Dark mode

Reload configuration
Open config folder
Quit
```

### Theme profile

Lists the profiles defined in the user's YAML configuration.

Selecting a profile:

1. Creates a safety snapshot.
2. Changes the wallpaper.
3. Resolves the selected Dark or Light variant.
4. Applies the required appearance changes.
5. Updates the active profile in the tray.

### Dark mode

The Dark Mode toggle controls which variant of the current profile is used.

- Enabled: uses Dark variants
- Disabled: uses Light variants

Changing the mode does not change the selected profile or wallpaper.

---

## Configuration

The main configuration file is:

```text
~/.config/cinnameleon/config.yaml
```

An example configuration is available in:

```text
data/config.example.yaml
```

A typical configuration looks like this:

```yaml
wallpaper_directory: ~/Pictures/Wallpapers

defaults:
  gtk_theme:
    dark: Mint-Y-Dark
    light: Mint-Y

  cinnamon_theme:
    dark: Mint-Y-Dark
    light: Mint-Y

  window_borders:
    dark: Mint-Y
    light: Mint-Y

  icon_theme:
    dark: Mint-Y
    light: Mint-Y

  cursor_theme:
    dark: Bibata-Modern-Classic
    light: Bibata-Modern-Classic

  fonts:
    interface: "Sans 10"
    document: "Sans 10"
    monospace: "Monospace 10"
    window_title: "Sans Bold 10"

profiles:
  - id: ocean
    name: Ocean
    wallpaper: ocean.jpg

  - id: forest
    name: Forest
    wallpaper: forest.jpg

    appearance:
      gtk_theme:
        dark: Mint-Y-Blue-Dark
        light: Mint-Y-Blue

      icon_theme:
        dark: Papirus-Dark
        light: Papirus
```

---

## Configuration reference

### `wallpaper_directory`

Directory containing the wallpapers used by all profiles.

```yaml
wallpaper_directory: ~/Pictures/Wallpapers
```

Profile wallpaper paths are relative to this directory.

```yaml
wallpaper: ocean.jpg
```

### `defaults`

Defines values shared by profiles that do not override them.

Supported appearance fields:

- `gtk_theme`
- `cinnamon_theme`
- `window_borders`
- `icon_theme`
- `cursor_theme`
- `fonts`

### Theme variants

Appearance fields can define separate Dark and Light values:

```yaml
gtk_theme:
  dark: Mint-Y-Dark
  light: Mint-Y
```

### Fonts

Supported font settings:

```yaml
fonts:
  interface: "Sans 10"
  document: "Sans 10"
  monospace: "Monospace 10"
  window_title: "Sans Bold 10"
```

### `profiles`

Every profile requires:

- A unique `id`
- A display `name`
- A unique `wallpaper`

```yaml
profiles:
  - id: ocean
    name: Ocean
    wallpaper: ocean.jpg
```

A wallpaper cannot be assigned to more than one profile.

### Profile overrides

Profiles may override individual defaults:

```yaml
profiles:
  - id: ocean
    name: Ocean
    wallpaper: ocean.jpg

    appearance:
      gtk_theme:
        dark: Mint-Y-Blue-Dark
        light: Mint-Y-Blue

      icon_theme:
        dark: Papirus-Dark
        light: Papirus
```

Values not overridden by the profile are inherited from `defaults`.

---

## Configuration reload

Cinnameleon monitors its configuration directory.

When `config.yaml` changes:

- A valid configuration is loaded automatically.
- The tray menu is rebuilt.
- Existing valid state is preserved.
- An invalid update does not replace the last valid configuration.

The configuration can also be reloaded manually through:

```text
Tray menu → Reload configuration
```

---

## Command-line interface

Show all available commands:

```bash
cinnameleon --help
```

When using the installed version directly:

```bash
~/.local/share/cinnameleon/venv/bin/cinnameleon --help
```

### Inspect the current desktop

```bash
cinnameleon inspect
```

Displays the current wallpaper, GTK theme, Cinnamon theme, window borders, icon theme, cursor theme, and fonts.

### Validate the configuration

```bash
cinnameleon check
```

Validates:

- YAML structure
- Profile IDs
- Wallpaper paths
- Duplicate wallpapers
- Installed themes
- Installed fonts

### Resolve a profile

```bash
cinnameleon resolve ocean --mode dark
```

Shows the final effective values after merging the profile with the defaults.

### Preview changes

```bash
cinnameleon apply ocean --mode dark --dry-run
```

### Apply a profile

```bash
cinnameleon apply ocean --mode dark
```

### Create a snapshot

```bash
cinnameleon snapshot
```

### Restore the latest snapshot

Preview:

```bash
cinnameleon restore --dry-run
```

Restore:

```bash
cinnameleon restore
```

### Watch wallpaper changes

```bash
cinnameleon watch --mode dark
```

### Run the resident tray application

```bash
cinnameleon run
```

Verbose mode:

```bash
cinnameleon run --verbose
```

---

## Safety and snapshots

Before applying appearance changes, Cinnameleon stores a safety snapshot at:

```text
~/.local/state/cinnameleon/snapshots/latest.json
```

Snapshots contain the managed appearance settings before the change.

They are written atomically and use private file permissions.

To restore the latest snapshot:

```bash
cinnameleon restore
```

### Cinnamon shell theme safety

Changing the Cinnamon shell theme while the desktop session is running may trigger shell instability on some systems.

For that reason, Cinnameleon does **not** change the Cinnamon shell theme by default during normal profile application.

The following appearance settings remain enabled:

- Wallpaper
- GTK theme
- Window borders
- Icons
- Cursor
- Fonts

Commands that explicitly expose Cinnamon theme changes require the appropriate opt-in flag:

```bash
cinnameleon apply ocean \
  --mode dark \
  --include-cinnamon-theme
```

Use this option carefully.

---

## Application state

The selected Dark or Light mode is stored at:

```text
~/.local/state/cinnameleon/state.json
```

The active profile does not need to be stored separately because it is resolved from the current wallpaper.

---

## Logs

Logs are stored at:

```text
~/.local/state/cinnameleon/cinnameleon.log
```

Follow the log in real time:

```bash
tail -f ~/.local/state/cinnameleon/cinnameleon.log
```

Run with console debug logging:

```bash
cinnameleon run --verbose
```

---

## File locations

| Purpose | Location |
|---|---|
| Installed application | `~/.local/share/cinnameleon/` |
| Executable | `~/.local/share/cinnameleon/venv/bin/cinnameleon` |
| Configuration | `~/.config/cinnameleon/config.yaml` |
| Application state | `~/.local/state/cinnameleon/state.json` |
| Snapshots | `~/.local/state/cinnameleon/snapshots/` |
| Log file | `~/.local/state/cinnameleon/cinnameleon.log` |
| Application launcher | `~/.local/share/applications/io.github.goncalosamp27.cinnameleon.desktop` |
| Autostart entry | `~/.config/autostart/io.github.goncalosamp27.cinnameleon.desktop` |
| Application icon | `~/.local/share/icons/hicolor/scalable/apps/` |
| Tray icon | `~/.local/share/icons/hicolor/scalable/status/` |

---

## Updating

Pull the latest project changes:

```bash
git pull
```

Run the installer again:

```bash
./scripts/install.sh
```

The installer reuses the private Python environment and preserves the existing configuration.

---

## Uninstallation

Remove the installed application:

```bash
./scripts/uninstall.sh
```

By default, the uninstaller preserves:

```text
~/.config/cinnameleon/
~/.local/state/cinnameleon/
~/Pictures/Cinnameleon/
```

To also remove the configuration, logs, snapshots, and saved state:

```bash
./scripts/uninstall.sh --purge
```

User wallpapers are always preserved.

Show uninstaller options:

```bash
./scripts/uninstall.sh --help
```

---

## Development setup

Clone the repository:

```bash
git clone https://github.com/goncalosamp27/Cinnameleon.git
cd Cinnameleon
```

Create a development environment with access to system GTK packages:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

Install the project in editable mode:

```bash
python -m pip install --editable . --no-deps
```

Run the application:

```bash
cinnameleon run --verbose
```

---

## Tests

Compile the source and tests:

```bash
python -m compileall -q src tests
```

Run the unit test suite:

```bash
python -m unittest discover -s tests -v
```

Validate installer scripts:

```bash
bash -n scripts/install.sh
bash -n scripts/uninstall.sh
```

Validate desktop entries after installation:

```bash
desktop-file-validate \
  ~/.local/share/applications/io.github.goncalosamp27.cinnameleon.desktop

desktop-file-validate \
  ~/.config/autostart/io.github.goncalosamp27.cinnameleon.desktop
```

---

## Project structure

```text
Cinnameleon/
├── assets/
│   └── icons/
│       ├── io.github.goncalosamp27.cinnameleon.svg
│       └── io.github.goncalosamp27.cinnameleon-tray-symbolic.svg
├── data/
│   └── config.example.yaml
├── scripts/
│   ├── install.sh
│   └── uninstall.sh
├── src/
│   └── cinnameleon/
│       ├── application.py
│       ├── cli.py
│       ├── config.py
│       ├── inspector.py
│       ├── logging_setup.py
│       ├── models.py
│       ├── resolver.py
│       ├── settings_backend.py
│       ├── snapshot.py
│       ├── state.py
│       ├── tray.py
│       ├── validator.py
│       └── watcher.py
├── tests/
├── pyproject.toml
└── README.md
```

---

## Architecture overview

Cinnameleon is split into focused modules:

- `config.py` loads and structurally validates YAML.
- `validator.py` checks themes, cursors, icons, and fonts installed on the system.
- `resolver.py` merges defaults, profile overrides, and the selected mode.
- `settings_backend.py` maps profiles to `Gio.Settings` and applies only required changes.
- `snapshot.py` captures and restores safety snapshots.
- `watcher.py` listens for wallpaper changes.
- `tray.py` provides the native Cinnamon tray interface.
- `application.py` coordinates the resident application.
- `state.py` stores persistent runtime preferences.
- `cli.py` exposes commands for inspection, validation, application, restore, watching, and runtime operation.

---

## Known limitations

- Cinnameleon currently targets Linux Mint Cinnamon.
- Only local wallpaper files are supported.
- Wallpapers must be unique across profiles.
- The Cinnamon shell theme is skipped by default for session stability.
- There is currently no graphical profile editor.
- Profiles are edited directly in YAML.
- The project still requires testing across more Cinnamon versions and clean installations.
- The application and tray artwork may still change before the stable release.

---

## Roadmap

Planned improvements include:

- Graphical profile editor
- First-run setup flow
- Theme and wallpaper picker
- Profile import and export
- Better validation feedback in the tray
- Packaged distribution format
- Automated release builds
- Broader Cinnamon version testing
- Improved accessibility and translations

---

## Contributing

Contributions, bug reports, and test results are welcome.

Before submitting changes:

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -v
bash -n scripts/install.sh
bash -n scripts/uninstall.sh
```

When reporting a bug, include:

- Linux Mint version
- Cinnamon version
- Python version
- Relevant Cinnameleon log output
- A sanitized configuration example
- Steps required to reproduce the issue

Do not include private wallpaper paths or personal information in public issue reports.

---

## Security and privacy

Cinnameleon runs locally.

It does not:

- Upload wallpapers
- Send theme information to external services
- Track user activity
- Require an online account
- Use background polling

The application reads and modifies only the desktop settings required to manage appearance profiles.

---

## License

A license has not yet been selected.

Before publishing a stable release, add a `LICENSE` file and update this section. Common choices for this type of project include MIT, Apache-2.0, and GPL-3.0.

---

## Acknowledgements

Cinnameleon is built with:

- Python
- PyGObject
- GTK 3
- Gio
- XApp
- PyYAML
- Linux Mint Cinnamon

---

## Status

Cinnameleon is currently an alpha project.

It is ready for:

- Personal use
- Technical testing
- Feedback from Linux Mint Cinnamon users

It should not yet be considered a production-stable desktop utility.
