"""Read the current Linux Mint Cinnamon appearance settings."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Any

import gi

gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("XApp", "1.0")

from gi.repository import Gio, Gtk, XApp


@dataclass(frozen=True)
class SettingSpec:
    """Description of a GSettings value used by Cinnameleon."""

    label: str
    schema_id: str
    key: str


APPEARANCE_SETTINGS = (
    SettingSpec(
        label="Wallpaper URI",
        schema_id="org.cinnamon.desktop.background",
        key="picture-uri",
    ),
    SettingSpec(
        label="GTK theme",
        schema_id="org.cinnamon.desktop.interface",
        key="gtk-theme",
    ),
    SettingSpec(
        label="Cinnamon theme",
        schema_id="org.cinnamon.theme",
        key="name",
    ),
    SettingSpec(
        label="Window borders",
        schema_id="org.cinnamon.desktop.wm.preferences",
        key="theme",
    ),
    SettingSpec(
        label="Icon theme",
        schema_id="org.cinnamon.desktop.interface",
        key="icon-theme",
    ),
    SettingSpec(
        label="Cursor theme",
        schema_id="org.cinnamon.desktop.interface",
        key="cursor-theme",
    ),
    SettingSpec(
        label="Interface font",
        schema_id="org.cinnamon.desktop.interface",
        key="font-name",
    ),
    SettingSpec(
        label="Document font",
        schema_id="org.gnome.desktop.interface",
        key="document-font-name",
    ),
    SettingSpec(
        label="Monospace font",
        schema_id="org.gnome.desktop.interface",
        key="monospace-font-name",
    ),
    SettingSpec(
        label="Window title font",
        schema_id="org.cinnamon.desktop.wm.preferences",
        key="titlebar-font",
    ),
)


def _get_cinnamon_version() -> str:
    """Return the installed Cinnamon version without starting Cinnamon."""

    try:
        result = subprocess.run(
            ["cinnamon", "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "Unavailable"

    output = result.stdout.strip() or result.stderr.strip()
    return output or "Unavailable"


def _get_schema(schema_id: str) -> Gio.SettingsSchema | None:
    """Find a GSettings schema without raising an exception."""

    source = Gio.SettingsSchemaSource.get_default()

    if source is None:
        return None

    return source.lookup(schema_id, True)


def _read_setting(spec: SettingSpec) -> Any:
    """Read a setting after confirming that its schema and key exist."""

    schema = _get_schema(spec.schema_id)

    if schema is None:
        return f"Unavailable: schema {spec.schema_id!r} was not found"

    if not schema.has_key(spec.key):
        return f"Unavailable: key {spec.key!r} was not found"

    settings = Gio.Settings.new_full(schema, None, None)
    return settings.get_value(spec.key).unpack()


def _wallpaper_path(uri: str) -> str | None:
    """Convert a local wallpaper URI into a normal filesystem path."""

    if not uri:
        return None

    try:
        return Gio.File.new_for_uri(uri).get_path()
    except TypeError:
        return None


def inspect_system() -> list[tuple[str, str]]:
    """Collect information about the current Cinnamon environment."""

    results: list[tuple[str, str]] = [
        ("Desktop", os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")),
        ("Session", os.environ.get("DESKTOP_SESSION", "Unknown")),
        ("Cinnamon", _get_cinnamon_version()),
        ("Python", platform.python_version()),
        (
            "GTK",
            (
                f"{Gtk.get_major_version()}."
                f"{Gtk.get_minor_version()}."
                f"{Gtk.get_micro_version()}"
            ),
        ),
        (
            "XApp StatusIcon",
            "Available" if hasattr(XApp, "StatusIcon") else "Unavailable",
        ),
    ]

    for spec in APPEARANCE_SETTINGS:
        value = _read_setting(spec)
        results.append((spec.label, str(value)))

        if spec.key == "picture-uri" and isinstance(value, str):
            path = _wallpaper_path(value)

            if path:
                results.append(("Wallpaper path", path))

    return results


def print_inspection() -> None:
    """Print the current Cinnamon configuration."""

    results = inspect_system()
    label_width = max(len(label) for label, _ in results)

    print("Cinnameleon system inspection")
    print("=" * 32)

    for label, value in results:
        print(f"{label:<{label_width}} : {value}")