# Cinnameleon

Cinnameleon is a lightweight appearance profile manager for Linux Mint Cinnamon.

It was created from a simple frustration: changing the look of the desktop usually means configuring several things separately such as GTK themes, icons, cursors, fonts, terminal colors and wallpapers.

Cinnameleon groups all of that into appearance profiles and keeps the desktop synchronized with the selected profile.

## What it does

A Cinnameleon profile can control:

- GTK theme
- Cinnamon theme
- Window borders
- Icon theme
- Cursor theme
- Fonts
- GNOME Terminal color palette
- Wallpaper
- Light and dark variants

Profiles are stored in a human-readable YAML configuration and can be managed through the Cinnameleon GUI or directly from the configuration file.

Cinnameleon can also detect wallpaper changes and apply the corresponding appearance profile automatically.

A tray icon provides quick access to:

- Open the GUI
- Switch profile
- Toggle dark mode
- Reload the configuration
- Open the configuration folder

## Motivation

The goal of Cinnameleon is not to replace Cinnamon's appearance settings.

It sits on top of them and makes complete desktop setups easier to save, switch and reproduce.

Instead of thinking about individual themes, icons or colors, Cinnameleon treats the desktop appearance as a single profile.

## Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/goncalosamp27/Cinnameleon.git
cd Cinnameleon
bash scripts/install.sh
```

Cinnameleon is installed for the current user and starts automatically with the Cinnamon session.

To install without automatic startup:

```bash
bash scripts/install.sh --no-autostart
```

Cinnameleon is currently under development.
