# Theme Profiles for Linux Mint Cinnamon (Cinnameleon)

## Software Requirements Specification (Version 1.0)

------------------------------------------------------------------------

# Overview

Develop a native desktop application for **Linux Mint Cinnamon** that
manages complete desktop appearance profiles.

The application should integrate naturally with Cinnamon, live in the
System Tray (Notification Area), and automatically synchronize
wallpapers with desktop appearance.

A profile represents the entire visual identity of the desktop.

Changing the wallpaper (or manually selecting a profile) should
automatically apply all configured appearance components.

The application should feel like an official Linux Mint utility.

------------------------------------------------------------------------

# Design Goals

The application must be:

-   Lightweight
-   Fast
-   Native looking
-   Modular
-   Robust
-   Easy to extend
-   Event-driven (avoid polling whenever possible)

The configuration must be entirely YAML-based.

The YAML file is the single source of truth.

Version 1 intentionally excludes any GUI profile editor.

------------------------------------------------------------------------

# Appearance Components

A profile may configure:

-   Wallpaper
-   GTK Theme
-   Cinnamon Theme
-   Window Borders
-   Icon Theme
-   Cursor Theme
-   Desktop Icons Theme
-   Fonts
    -   Interface
    -   Document
    -   Monospace
    -   Window Title

Every component is optional.

If omitted, the corresponding default value must be used.

------------------------------------------------------------------------

# Tray Application

The application should automatically start with the user session.

The tray icon should be a **chameleon**.

Example menu:

``` text
🎨 Theme Profiles

Current Profile
✓ Gengar

────────────────────

Mode
● Dark
○ Light

────────────────────

Profiles

Gengar
Bulbasaur
Charizard

────────────────────

Reload Configuration
Open Config Folder
Quit
```

The tray menu must allow:

-   View current profile
-   Toggle Dark / Light mode
-   Select another profile
-   Reload configuration
-   Open configuration folder
-   Quit application

------------------------------------------------------------------------

# Main Window

A small GTK read-only status window displaying the current profile,
wallpaper, mode, appearance components, configuration path and status.

------------------------------------------------------------------------

# YAML Configuration

``` yaml
wallpaper_directory: ~/Pictures/Wallpapers

defaults:

  gtk_theme:
    dark: Mint-Y-Dark
    light: Mint-Y

  cinnamon_theme:
    dark: Mint-Y-Dark
    light: Mint-Y

  window_borders:
    dark: Mint-Y-Dark
    light: Mint-Y

  icon_theme:
    dark: Papirus-Dark
    light: Papirus

  cursor_theme:
    dark: Bibata-Modern-Ice
    light: Bibata-Modern-Ice

  desktop_icons:
    dark: Mint-Y
    light: Mint-Y

  fonts:
    interface: "Inter 10"
    document: "Noto Sans 10"
    monospace: "JetBrains Mono 10"
    window_title: "Inter Bold 10"

profiles:

  - id: gengar
    name: Gengar
    wallpaper: Pokemon/Gengar.png

    gtk_theme:
      dark: Mint-Purple
      light: Mint-Purple-Light

    cinnamon_theme:
      dark: Mint-Purple
      light: Mint-Purple-Light

    window_borders:
      dark: Mint-Purple
      light: Mint-Purple-Light

    icon_theme:
      dark: PurpleFolders
      light: PurpleFolders-Light

    cursor_theme:
      dark: Bibata-Purple

    fonts:
      interface: "Inter 10"
      monospace: "JetBrains Mono 10"

  - id: bulbasaur
    name: Bulbasaur
    wallpaper: Pokemon/Bulbasaur.png
```

The wallpaper path is resolved as:

`wallpaper_directory + wallpaper`

------------------------------------------------------------------------

# Validation

Validate at startup and reload:

-   wallpaper_directory exists
-   wallpaper exists
-   GTK theme exists
-   Cinnamon theme exists
-   Window border theme exists
-   Icon theme exists
-   Cursor theme exists
-   Desktop icon theme exists
-   Fonts exist (Fontconfig)

Rules:

-   Invalid profiles are ignored.
-   Invalid profiles never appear in the tray or UI.
-   Missing values fall back to defaults.
-   If both profile and default values are invalid, keep the current
    system value and log a warning.
-   Never crash because of configuration errors.

------------------------------------------------------------------------

# Wallpaper Detection

Use GSettings/Gio signals.

When wallpaper changes:

1.  Read wallpaper
2.  Resolve full path
3.  Find matching profile
4.  Apply appearance
5.  Update tray

No polling.

------------------------------------------------------------------------

# Manual Profile Selection

Selecting a profile:

1.  Changes wallpaper
2.  Applies all appearance components
3.  Updates current profile

------------------------------------------------------------------------

# Dark / Light

Dark/Light is global.

Switching mode changes only the corresponding appearance variants, never
the profile.

------------------------------------------------------------------------

# Architecture

``` text
theme-profiles/

app.py
tray.py
watcher.py
theme_manager.py
config.py
settings.py
models.py
logger.py
resources/
ui/
config.yaml
```

ThemeManager delegates to:

-   WallpaperApplier
-   GtkThemeApplier
-   CinnamonThemeApplier
-   WindowBorderApplier
-   IconThemeApplier
-   CursorThemeApplier
-   DesktopIconsApplier
-   FontApplier

Each implements:

``` python
apply(profile, mode)
```

------------------------------------------------------------------------

# Technologies

-   Python 3
-   GTK4
-   PyGObject
-   AppIndicator
-   Gio
-   GSettings
-   PyYAML

------------------------------------------------------------------------

# Future Features

Not part of v1:

-   GUI Profile Editor
-   Profile Wizard
-   Import / Export
-   Theme Preview
-   Sunrise / Sunset switching
-   Multiple monitors
-   Accent colors
-   Terminal theme
-   VSCode theme
-   Firefox theme
-   Discord theme
-   Custom post-apply scripts

------------------------------------------------------------------------

# Expected Behaviour

The application should feel like an official Linux Mint utility.

The user edits only:

`~/.config/theme-profiles/config.yaml`

The application validates the configuration, exposes only valid
profiles, and instantly applies the complete desktop appearance whenever
the wallpaper changes or a profile is manually selected.