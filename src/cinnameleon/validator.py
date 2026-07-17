"""Validate appearance resources installed on the current system."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Callable

import gi

gi.require_version("Pango", "1.0")

from gi.repository import Pango

from cinnameleon.models import (
    AppearanceSettings,
    Configuration,
    ConfigIssue,
    FontSettings,
    IssueLevel,
    ThemeVariants,
)


ResourceValidator = Callable[[str], bool]


def _unique_paths(paths: list[Path]) -> tuple[Path, ...]:
    """Return unique paths while preserving their original order."""

    unique: list[Path] = []
    seen: set[Path] = set()

    for path in paths:
        expanded = path.expanduser()

        if expanded not in seen:
            seen.add(expanded)
            unique.append(expanded)

    return tuple(unique)


def _xdg_data_directories() -> tuple[Path, ...]:
    """Return user and system XDG data directories."""

    user_data_home = Path(
        os.environ.get(
            "XDG_DATA_HOME",
            str(Path.home() / ".local" / "share"),
        )
    )

    system_data_value = os.environ.get(
        "XDG_DATA_DIRS",
        "/usr/local/share:/usr/share",
    )

    system_data_directories = [
        Path(value)
        for value in system_data_value.split(":")
        if value
    ]

    return _unique_paths(
        [
            user_data_home,
            *system_data_directories,
        ]
    )


def theme_directories() -> tuple[Path, ...]:
    """Return locations that may contain desktop themes."""

    return _unique_paths(
        [
            Path.home() / ".themes",
            *(
                directory / "themes"
                for directory in _xdg_data_directories()
            ),
        ]
    )


def icon_directories() -> tuple[Path, ...]:
    """Return locations that may contain icon and cursor themes."""

    return _unique_paths(
        [
            Path.home() / ".icons",
            *(
                directory / "icons"
                for directory in _xdg_data_directories()
            ),
        ]
    )


@lru_cache(maxsize=None)
def gtk_theme_exists(name: str) -> bool:
    """Return whether a GTK3 theme exists."""

    for directory in theme_directories():
        theme_directory = directory / name

        if (theme_directory / "gtk-3.0" / "gtk.css").is_file():
            return True

    return False


@lru_cache(maxsize=None)
def cinnamon_theme_exists(name: str) -> bool:
    """Return whether a Cinnamon shell theme exists."""

    for directory in theme_directories():
        theme_directory = directory / name

        if (
            theme_directory
            / "cinnamon"
            / "cinnamon.css"
        ).is_file():
            return True

    return False


@lru_cache(maxsize=None)
def window_border_theme_exists(name: str) -> bool:
    """Return whether a Metacity/Muffin window border theme exists."""

    for directory in theme_directories():
        metacity_directory = directory / name / "metacity-1"

        if not metacity_directory.is_dir():
            continue

        if any(
            metacity_directory.glob("metacity-theme-*.xml")
        ):
            return True

    return False


@lru_cache(maxsize=None)
def icon_theme_exists(name: str) -> bool:
    """Return whether an icon theme exists."""

    for directory in icon_directories():
        icon_directory = directory / name

        if (
            icon_directory.is_dir()
            and (icon_directory / "index.theme").is_file()
        ):
            return True

    return False


@lru_cache(maxsize=None)
def cursor_theme_exists(name: str) -> bool:
    """Return whether a cursor theme exists."""

    for directory in icon_directories():
        cursor_directory = directory / name

        if (
            cursor_directory.is_dir()
            and (cursor_directory / "cursors").is_dir()
        ):
            return True

    return False


def _normalize_font_family(value: str) -> str:
    """Normalize a font family for comparison."""

    return " ".join(value.casefold().split())


def _font_family_from_description(description: str) -> str | None:
    """Extract the family from a Pango font description."""

    font_description = Pango.FontDescription.from_string(
        description
    )

    family = font_description.get_family()

    if family is None:
        return None

    family = family.strip()

    return family or None


@lru_cache(maxsize=None)
def font_exists(description: str) -> bool:
    """Return whether the requested font family is installed."""

    family = _font_family_from_description(description)

    if family is None:
        return False

    normalized_family = _normalize_font_family(family)

    generic_families = {
        "sans",
        "sans-serif",
        "serif",
        "monospace",
        "system-ui",
    }

    if normalized_family in generic_families:
        return True

    try:
        result = subprocess.run(
            [
                "fc-match",
                "--format=%{family}\n",
                family,
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if result.returncode != 0:
        return False

    matched_families: set[str] = set()

    for line in result.stdout.splitlines():
        for matched_family in line.split(","):
            normalized = _normalize_font_family(
                matched_family
            )

            if normalized:
                matched_families.add(normalized)

    return normalized_family in matched_families


def _add_missing_resource_issue(
    issues: list[ConfigIssue],
    location: str,
    resource_type: str,
    resource_name: str,
) -> None:
    """Add an error for a missing appearance resource."""

    issues.append(
        ConfigIssue(
            level=IssueLevel.ERROR,
            location=location,
            message=(
                f"{resource_type} was not found: "
                f"{resource_name}"
            ),
        )
    )


def _validate_variants(
    variants: ThemeVariants,
    location: str,
    resource_type: str,
    validator: ResourceValidator,
    issues: list[ConfigIssue],
) -> None:
    """Validate dark and light variants of one resource."""

    values = {
        "dark": variants.dark,
        "light": variants.light,
    }

    for mode, resource_name in values.items():
        if resource_name is None:
            continue

        if not validator(resource_name):
            _add_missing_resource_issue(
                issues=issues,
                location=f"{location}.{mode}",
                resource_type=resource_type,
                resource_name=resource_name,
            )


def _validate_fonts(
    fonts: FontSettings,
    location: str,
    issues: list[ConfigIssue],
) -> None:
    """Validate every configured font family."""

    values = {
        "interface": fonts.interface,
        "document": fonts.document,
        "monospace": fonts.monospace,
        "window_title": fonts.window_title,
    }

    for font_type, description in values.items():
        if description is None:
            continue

        if not font_exists(description):
            _add_missing_resource_issue(
                issues=issues,
                location=f"{location}.{font_type}",
                resource_type="Font",
                resource_name=description,
            )


def _validate_appearance(
    appearance: AppearanceSettings,
    location: str,
    issues: list[ConfigIssue],
) -> None:
    """Validate all resources in an appearance configuration."""

    _validate_variants(
        variants=appearance.gtk_theme,
        location=f"{location}.gtk_theme",
        resource_type="GTK theme",
        validator=gtk_theme_exists,
        issues=issues,
    )

    _validate_variants(
        variants=appearance.cinnamon_theme,
        location=f"{location}.cinnamon_theme",
        resource_type="Cinnamon theme",
        validator=cinnamon_theme_exists,
        issues=issues,
    )

    _validate_variants(
        variants=appearance.window_borders,
        location=f"{location}.window_borders",
        resource_type="Window border theme",
        validator=window_border_theme_exists,
        issues=issues,
    )

    _validate_variants(
        variants=appearance.icon_theme,
        location=f"{location}.icon_theme",
        resource_type="Icon theme",
        validator=icon_theme_exists,
        issues=issues,
    )

    _validate_variants(
        variants=appearance.cursor_theme,
        location=f"{location}.cursor_theme",
        resource_type="Cursor theme",
        validator=cursor_theme_exists,
        issues=issues,
    )

    _validate_fonts(
        fonts=appearance.fonts,
        location=f"{location}.fonts",
        issues=issues,
    )


def validate_configuration_resources(
    config: Configuration,
) -> tuple[ConfigIssue, ...]:
    """Validate every system resource referenced by a configuration."""

    issues: list[ConfigIssue] = []

    _validate_appearance(
        appearance=config.defaults,
        location="defaults",
        issues=issues,
    )

    for index, profile in enumerate(config.profiles):
        if not profile.wallpaper.is_file():
            _add_missing_resource_issue(
                issues=issues,
                location=f"profiles[{index}].wallpaper",
                resource_type="Wallpaper",
                resource_name=str(profile.wallpaper),
            )

        _validate_appearance(
            appearance=profile.appearance,
            location=f"profiles[{index}]",
            issues=issues,
        )

    return tuple(issues)