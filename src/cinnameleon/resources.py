"""Discover appearance resources installed on the current system."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable


ResourceMatcher = Callable[[Path], bool]


def _unique_paths(paths: list[Path]) -> tuple[Path, ...]:
    """Return unique expanded paths while preserving order."""

    unique: list[Path] = []
    seen: set[Path] = set()

    for path in paths:
        expanded = path.expanduser()

        if expanded in seen:
            continue

        seen.add(expanded)
        unique.append(expanded)

    return tuple(unique)


def xdg_data_directories() -> tuple[Path, ...]:
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
                for directory in xdg_data_directories()
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
                for directory in xdg_data_directories()
            ),
        ]
    )


def _discover_resource_names(
    directories: tuple[Path, ...],
    matcher: ResourceMatcher,
) -> tuple[str, ...]:
    """Discover resource directory names matching a predicate."""

    names: set[str] = set()

    for directory in directories:
        if not directory.is_dir():
            continue

        try:
            children = tuple(directory.iterdir())
        except OSError:
            continue

        for child in children:
            if not child.is_dir():
                continue

            try:
                matches = matcher(child)
            except OSError:
                matches = False

            if matches:
                names.add(child.name)

    return tuple(sorted(names, key=str.casefold))


def _is_gtk_theme(path: Path) -> bool:
    return (path / "gtk-3.0" / "gtk.css").is_file()


def _is_cinnamon_theme(path: Path) -> bool:
    return (path / "cinnamon" / "cinnamon.css").is_file()


def _is_window_border_theme(path: Path) -> bool:
    metacity_directory = path / "metacity-1"

    return (
        metacity_directory.is_dir()
        and any(
            metacity_directory.glob(
                "metacity-theme-*.xml"
            )
        )
    )


def _is_icon_theme(path: Path) -> bool:
    return (path / "index.theme").is_file()


def _is_cursor_theme(path: Path) -> bool:
    return (path / "cursors").is_dir()


@lru_cache(maxsize=1)
def list_gtk_themes() -> tuple[str, ...]:
    """Return installed GTK3 theme names."""

    return _discover_resource_names(
        theme_directories(),
        _is_gtk_theme,
    )


@lru_cache(maxsize=1)
def list_cinnamon_themes() -> tuple[str, ...]:
    """Return installed Cinnamon shell theme names."""

    return _discover_resource_names(
        theme_directories(),
        _is_cinnamon_theme,
    )


@lru_cache(maxsize=1)
def list_window_border_themes() -> tuple[str, ...]:
    """Return installed Metacity/Muffin window border themes."""

    return _discover_resource_names(
        theme_directories(),
        _is_window_border_theme,
    )


@lru_cache(maxsize=1)
def list_icon_themes() -> tuple[str, ...]:
    """Return installed icon theme names."""

    return _discover_resource_names(
        icon_directories(),
        _is_icon_theme,
    )


@lru_cache(maxsize=1)
def list_cursor_themes() -> tuple[str, ...]:
    """Return installed cursor theme names."""

    return _discover_resource_names(
        icon_directories(),
        _is_cursor_theme,
    )


def _normalize_font_family(value: str) -> str:
    return " ".join(value.strip().split())


@lru_cache(maxsize=1)
def list_font_families() -> tuple[str, ...]:
    """Return installed font family names using fontconfig."""

    try:
        result = subprocess.run(
            [
                "fc-list",
                ":",
                "family",
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ()

    if result.returncode != 0:
        return ()

    families: set[str] = set()

    for line in result.stdout.splitlines():
        for family in line.split(","):
            normalized = _normalize_font_family(
                family
            )

            if normalized:
                families.add(normalized)

    return tuple(
        sorted(
            families,
            key=str.casefold,
        )
    )


@lru_cache(maxsize=None)
def gtk_theme_exists(name: str) -> bool:
    """Return whether a GTK3 theme exists."""

    return name in list_gtk_themes()


@lru_cache(maxsize=None)
def cinnamon_theme_exists(name: str) -> bool:
    """Return whether a Cinnamon shell theme exists."""

    return name in list_cinnamon_themes()


@lru_cache(maxsize=None)
def window_border_theme_exists(name: str) -> bool:
    """Return whether a window border theme exists."""

    return name in list_window_border_themes()


@lru_cache(maxsize=None)
def icon_theme_exists(name: str) -> bool:
    """Return whether an icon theme exists."""

    return name in list_icon_themes()


@lru_cache(maxsize=None)
def cursor_theme_exists(name: str) -> bool:
    """Return whether a cursor theme exists."""

    return name in list_cursor_themes()


def refresh_resource_cache() -> None:
    """Clear cached discovery results after resources change."""

    list_gtk_themes.cache_clear()
    list_cinnamon_themes.cache_clear()
    list_window_border_themes.cache_clear()
    list_icon_themes.cache_clear()
    list_cursor_themes.cache_clear()
    list_font_families.cache_clear()

    gtk_theme_exists.cache_clear()
    cinnamon_theme_exists.cache_clear()
    window_border_theme_exists.cache_clear()
    icon_theme_exists.cache_clear()
    cursor_theme_exists.cache_clear()


@dataclass(frozen=True)
class ResourceCatalog:
    """Snapshot of appearance resources available to Cinnameleon."""

    gtk_themes: tuple[str, ...]
    cinnamon_themes: tuple[str, ...]
    window_border_themes: tuple[str, ...]
    icon_themes: tuple[str, ...]
    cursor_themes: tuple[str, ...]
    font_families: tuple[str, ...]

    @classmethod
    def discover(
        cls,
        *,
        refresh: bool = False,
    ) -> "ResourceCatalog":
        """Discover all supported appearance resources."""

        if refresh:
            refresh_resource_cache()

        return cls(
            gtk_themes=list_gtk_themes(),
            cinnamon_themes=list_cinnamon_themes(),
            window_border_themes=(
                list_window_border_themes()
            ),
            icon_themes=list_icon_themes(),
            cursor_themes=list_cursor_themes(),
            font_families=list_font_families(),
        )