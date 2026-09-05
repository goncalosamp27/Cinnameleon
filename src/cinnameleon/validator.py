"""Validate appearance resources installed on the current system."""

from __future__ import annotations

import subprocess
from functools import lru_cache
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
from cinnameleon.resources import (
    cinnamon_theme_exists,
    cursor_theme_exists,
    gtk_theme_exists,
    icon_theme_exists,
    window_border_theme_exists,
)


ResourceValidator = Callable[[str], bool]


def _normalize_font_family(value: str) -> str:
    """Normalize a font family for comparison."""

    return " ".join(value.casefold().split())


def _font_family_from_description(
    description: str,
) -> str | None:
    """Extract the family from a Pango font description."""

    font_description = (
        Pango.FontDescription.from_string(
            description
        )
    )

    family = font_description.get_family()

    if family is None:
        return None

    family = family.strip()

    return family or None


@lru_cache(maxsize=None)
def font_exists(description: str) -> bool:
    """Return whether the requested font family is installed."""

    family = _font_family_from_description(
        description
    )

    if family is None:
        return False

    normalized_family = _normalize_font_family(
        family
    )

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
    except (
        OSError,
        subprocess.SubprocessError,
    ):
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
                matched_families.add(
                    normalized
                )

    return (
        normalized_family
        in matched_families
    )


def _add_missing_resource_issue(
    issues: list[ConfigIssue],
    location: str,
    resource_type: str,
    resource_name: str,
) -> None:
    """Add an error for a missing appearance resource."""

    issues.append(
        ConfigIssue(
            level=IssueLevel.WARNING,
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
                location=(
                    f"{location}.{font_type}"
                ),
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
        location=(
            f"{location}.cinnamon_theme"
        ),
        resource_type="Cinnamon theme",
        validator=cinnamon_theme_exists,
        issues=issues,
    )

    _validate_variants(
        variants=appearance.window_borders,
        location=(
            f"{location}.window_borders"
        ),
        resource_type="Window border theme",
        validator=(
            window_border_theme_exists
        ),
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

    for index, profile in enumerate(
        config.profiles
    ):
        if not profile.wallpaper.is_file():
            _add_missing_resource_issue(
                issues=issues,
                location=(
                    f"profiles[{index}].wallpaper"
                ),
                resource_type="Wallpaper",
                resource_name=str(
                    profile.wallpaper
                ),
            )

        _validate_appearance(
            appearance=profile.appearance,
            location=f"profiles[{index}]",
            issues=issues,
        )

    return tuple(issues)