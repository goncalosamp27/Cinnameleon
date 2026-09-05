"""Load and structurally validate Cinnameleon YAML configuration."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from cinnameleon.models import (
    AppearanceSettings,
    Configuration,
    ConfigIssue,
    ConfigLoadResult,
    FontSettings,
    IssueLevel,
    Profile,
    ThemeVariants,
    ANSI_COLOR_KEYS,
    TerminalPalette,
    TerminalSettings,
)


PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

HEX_COLOR_PATTERN = re.compile(
    r"^#[0-9a-fA-F]{6}$"
)

ROOT_KEYS = {
    "wallpaper_directory",
    "defaults",
    "profiles",
}

APPEARANCE_KEYS = {
    "gtk_theme",
    "cinnamon_theme",
    "window_borders",
    "icon_theme",
    "cursor_theme",
    "fonts",
}

VARIANT_KEYS = {
    "dark",
    "light",
}

FONT_KEYS = {
    "interface",
    "document",
    "monospace",
    "window_title",
}

TERMINAL_KEYS = {
    "dark",
    "light",
}

TERMINAL_PALETTE_KEYS = {
    "background",
    "foreground",
    "cursor",
    "selection_background",
    "selection_foreground",
    "ansi",
}

ANSI_KEYS = set(
    ANSI_COLOR_KEYS
)

PROFILE_KEYS = {
    "id",
    "name",
    "wallpaper",
    "terminal",
    *APPEARANCE_KEYS,
}


def default_config_path() -> Path:
    """Return the default XDG configuration path."""

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")

    if xdg_config_home:
        config_directory = Path(xdg_config_home).expanduser()
    else:
        config_directory = Path.home() / ".config"

    return config_directory / "cinnameleon" / "config.yaml"


def resolve_config_path(path: Path | str | None = None) -> Path:
    """Resolve a user-provided or default configuration path."""

    if path is None:
        return default_config_path().resolve()

    return Path(path).expanduser().resolve()


def _add_error(
    issues: list[ConfigIssue],
    location: str,
    message: str,
) -> None:
    issues.append(
        ConfigIssue(
            level=IssueLevel.ERROR,
            location=location,
            message=message,
        )
    )


def _add_warning(
    issues: list[ConfigIssue],
    location: str,
    message: str,
) -> None:
    issues.append(
        ConfigIssue(
            level=IssueLevel.WARNING,
            location=location,
            message=message,
        )
    )


def _warn_unknown_keys(
    value: Mapping[str, Any],
    allowed_keys: set[str],
    location: str,
    issues: list[ConfigIssue],
) -> None:
    for key in value:
        if key not in allowed_keys:
            _add_warning(
                issues,
                f"{location}.{key}",
                "Unknown field; it will be ignored.",
            )


def _optional_string(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        _add_error(
            issues,
            location,
            "Expected a string.",
        )
        return None

    cleaned = value.strip()

    if not cleaned:
        _add_error(
            issues,
            location,
            "Value cannot be empty.",
        )
        return None

    return cleaned


def _required_string(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> str | None:
    if value is None:
        _add_error(
            issues,
            location,
            "Required field is missing.",
        )
        return None

    return _optional_string(value, location, issues)


def _parse_variants(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> ThemeVariants:
    if value is None:
        return ThemeVariants()

    # A string is accepted as shorthand for both modes.
    if isinstance(value, str):
        parsed = _optional_string(value, location, issues)

        return ThemeVariants(
            dark=parsed,
            light=parsed,
        )

    if not isinstance(value, Mapping):
        _add_error(
            issues,
            location,
            "Expected a string or a mapping with dark/light variants.",
        )
        return ThemeVariants()

    _warn_unknown_keys(
        value,
        VARIANT_KEYS,
        location,
        issues,
    )

    return ThemeVariants(
        dark=_optional_string(
            value.get("dark"),
            f"{location}.dark",
            issues,
        ),
        light=_optional_string(
            value.get("light"),
            f"{location}.light",
            issues,
        ),
    )


def _parse_fonts(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> FontSettings:
    if value is None:
        return FontSettings()

    if not isinstance(value, Mapping):
        _add_error(
            issues,
            location,
            "Expected a mapping of font names.",
        )
        return FontSettings()

    _warn_unknown_keys(
        value,
        FONT_KEYS,
        location,
        issues,
    )

    return FontSettings(
        interface=_optional_string(
            value.get("interface"),
            f"{location}.interface",
            issues,
        ),
        document=_optional_string(
            value.get("document"),
            f"{location}.document",
            issues,
        ),
        monospace=_optional_string(
            value.get("monospace"),
            f"{location}.monospace",
            issues,
        ),
        window_title=_optional_string(
            value.get("window_title"),
            f"{location}.window_title",
            issues,
        ),
    )

def _parse_hex_color(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> str | None:
    color = _required_string(
        value,
        location,
        issues,
    )

    if color is None:
        return None

    if not HEX_COLOR_PATTERN.fullmatch(
        color
    ):
        _add_error(
            issues,
            location,
            (
                "Expected a hexadecimal color "
                "in #RRGGBB format."
            ),
        )

        return None

    return color.upper()


def _parse_terminal_palette(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> TerminalPalette | None:
    if value is None:
        return None

    if not isinstance(
        value,
        Mapping,
    ):
        _add_error(
            issues,
            location,
            "Expected a terminal palette mapping.",
        )

        return None

    _warn_unknown_keys(
        value,
        TERMINAL_PALETTE_KEYS,
        location,
        issues,
    )

    background = _parse_hex_color(
        value.get("background"),
        f"{location}.background",
        issues,
    )

    foreground = _parse_hex_color(
        value.get("foreground"),
        f"{location}.foreground",
        issues,
    )

    cursor = _parse_hex_color(
        value.get("cursor"),
        f"{location}.cursor",
        issues,
    )

    selection_background = _parse_hex_color(
        value.get(
            "selection_background"
        ),
        (
            f"{location}."
            "selection_background"
        ),
        issues,
    )

    selection_foreground = _parse_hex_color(
        value.get(
            "selection_foreground"
        ),
        (
            f"{location}."
            "selection_foreground"
        ),
        issues,
    )

    raw_ansi = value.get(
        "ansi"
    )

    ansi: list[str] = []

    if not isinstance(
        raw_ansi,
        Mapping,
    ):
        _add_error(
            issues,
            f"{location}.ansi",
            (
                "Expected a mapping containing "
                "the 16 ANSI colors."
            ),
        )

    else:
        _warn_unknown_keys(
            raw_ansi,
            ANSI_KEYS,
            f"{location}.ansi",
            issues,
        )

        for key in ANSI_COLOR_KEYS:
            color = _parse_hex_color(
                raw_ansi.get(key),
                f"{location}.ansi.{key}",
                issues,
            )

            if color is not None:
                ansi.append(
                    color
                )

    if (
        background is None
        or foreground is None
        or cursor is None
        or selection_background
        is None
        or selection_foreground
        is None
        or len(ansi) != 16
    ):
        return None

    return TerminalPalette(
        background=background,
        foreground=foreground,
        cursor=cursor,
        selection_background=(
            selection_background
        ),
        selection_foreground=(
            selection_foreground
        ),
        ansi=tuple(
            ansi
        ),
    )


def _parse_terminal(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> TerminalSettings:
    if value is None:
        return TerminalSettings()

    if not isinstance(
        value,
        Mapping,
    ):
        _add_error(
            issues,
            location,
            (
                "Expected a mapping with "
                "dark/light terminal palettes."
            ),
        )

        return TerminalSettings()

    _warn_unknown_keys(
        value,
        TERMINAL_KEYS,
        location,
        issues,
    )

    return TerminalSettings(
        dark=_parse_terminal_palette(
            value.get("dark"),
            f"{location}.dark",
            issues,
        ),
        light=_parse_terminal_palette(
            value.get("light"),
            f"{location}.light",
            issues,
        ),
    )

def _parse_defaults(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> tuple[
    AppearanceSettings,
    TerminalSettings,
]:
    """
    Parse global defaults.

    Desktop appearance and terminal palettes live
    together under the YAML `defaults` mapping.
    """

    if value is None:
        return (
            AppearanceSettings(),
            TerminalSettings(),
        )

    if not isinstance(
        value,
        Mapping,
    ):
        _add_error(
            issues,
            location,
            "Expected a defaults mapping.",
        )

        return (
            AppearanceSettings(),
            TerminalSettings(),
        )

    # _parse_appearance() should not see `terminal`,
    # otherwise it considers it an unknown appearance key.
    appearance_value = {
        key: item
        for key, item in value.items()
        if key != "terminal"
    }

    appearance = _parse_appearance(
        appearance_value,
        location,
        issues,
    )

    terminal = _parse_terminal(
        value.get("terminal"),
        f"{location}.terminal",
        issues,
    )

    return (
        appearance,
        terminal,
    )

def _parse_appearance(
    value: Any,
    location: str,
    issues: list[ConfigIssue],
) -> AppearanceSettings:
    if value is None:
        return AppearanceSettings()

    if not isinstance(value, Mapping):
        _add_error(
            issues,
            location,
            "Expected an appearance mapping.",
        )
        return AppearanceSettings()

    _warn_unknown_keys(
        value,
        APPEARANCE_KEYS,
        location,
        issues,
    )

    return AppearanceSettings(
        gtk_theme=_parse_variants(
            value.get("gtk_theme"),
            f"{location}.gtk_theme",
            issues,
        ),
        cinnamon_theme=_parse_variants(
            value.get("cinnamon_theme"),
            f"{location}.cinnamon_theme",
            issues,
        ),
        window_borders=_parse_variants(
            value.get("window_borders"),
            f"{location}.window_borders",
            issues,
        ),
        icon_theme=_parse_variants(
            value.get("icon_theme"),
            f"{location}.icon_theme",
            issues,
        ),
        cursor_theme=_parse_variants(
            value.get("cursor_theme"),
            f"{location}.cursor_theme",
            issues,
        ),
        fonts=_parse_fonts(
            value.get("fonts"),
            f"{location}.fonts",
            issues,
        ),
    )


def _resolve_wallpaper_directory(
    raw_value: Any,
    config_path: Path,
    issues: list[ConfigIssue],
) -> Path | None:
    value = _required_string(
        raw_value,
        "wallpaper_directory",
        issues,
    )

    if value is None:
        return None

    directory = Path(value).expanduser()

    if not directory.is_absolute():
        directory = config_path.parent / directory

    directory = directory.resolve()

    if not directory.exists():
        _add_warning(
            issues,
            "wallpaper_directory",
            f"Directory does not exist: {directory}",
        )

    elif not directory.is_dir():
        _add_error(
            issues,
            "wallpaper_directory",
            f"Path is not a directory: {directory}",
        )

    return directory


def _resolve_wallpaper(
    raw_value: Any,
    wallpaper_directory: Path,
    location: str,
    issues: list[ConfigIssue],
) -> Path | None:
    value = _required_string(
        raw_value,
        location,
        issues,
    )

    if value is None:
        return None

    relative_path = Path(value).expanduser()

    if relative_path.is_absolute():
        _add_error(
            issues,
            location,
            "Wallpaper must be relative to wallpaper_directory.",
        )
        return None

    wallpaper = (
        wallpaper_directory / relative_path
    ).resolve()

    try:
        wallpaper.relative_to(
            wallpaper_directory
        )
    except ValueError:
        _add_error(
            issues,
            location,
            (
                "Wallpaper cannot point outside "
                "wallpaper_directory."
            ),
        )
        return None

    # Do NOT check whether the file exists here.
    #
    # This function validates the configuration/path,
    # not the availability of the external resource.
    # Resource availability is handled by validator.py.

    return wallpaper


def _parse_profile(
    value: Any,
    index: int,
    wallpaper_directory: Path,
    existing_ids: set[str],
    issues: list[ConfigIssue],
) -> Profile | None:
    location = f"profiles[{index}]"
    errors_before = sum(
        issue.level is IssueLevel.ERROR
        for issue in issues
    )

    if not isinstance(value, Mapping):
        _add_error(
            issues,
            location,
            "Expected a profile mapping.",
        )
        return None

    _warn_unknown_keys(
        value,
        PROFILE_KEYS,
        location,
        issues,
    )

    profile_id = _required_string(
        value.get("id"),
        f"{location}.id",
        issues,
    )

    name = _required_string(
        value.get("name"),
        f"{location}.name",
        issues,
    )

    wallpaper = _resolve_wallpaper(
        value.get("wallpaper"),
        wallpaper_directory,
        f"{location}.wallpaper",
        issues,
    )

    if profile_id is not None:
        if not PROFILE_ID_PATTERN.fullmatch(profile_id):
            _add_error(
                issues,
                f"{location}.id",
                (
                    "ID must use lowercase letters, numbers, "
                    "hyphens or underscores."
                ),
            )
        elif profile_id in existing_ids:
            _add_error(
                issues,
                f"{location}.id",
                f"Duplicate profile ID: {profile_id}",
            )

    appearance_data = {
        key: value.get(key)
        for key in APPEARANCE_KEYS
        if key in value
    }

    appearance = _parse_appearance(
        appearance_data,
        location,
        issues,
    )

    errors_after = sum(
        issue.level is IssueLevel.ERROR
        for issue in issues
    )

    if (
        errors_after > errors_before
        or profile_id is None
        or name is None
        or wallpaper is None
    ):
        return None

    existing_ids.add(profile_id)

    return Profile(
        id=profile_id,
        name=name,
        wallpaper=wallpaper,
        appearance=appearance,
        terminal=_parse_terminal(
            value.get("terminal"),
            f"{location}.terminal",
            issues,
        ),
    )


def load_configuration(
    path: Path | str | None = None,
) -> ConfigLoadResult:
    """Load and validate a Cinnameleon YAML configuration."""

    config_path = resolve_config_path(path)
    issues: list[ConfigIssue] = []

    if not config_path.exists():
        _add_error(
            issues,
            "configuration",
            f"Configuration file does not exist: {config_path}",
        )
        return ConfigLoadResult(
            config=None,
            issues=tuple(issues),
        )

    if not config_path.is_file():
        _add_error(
            issues,
            "configuration",
            f"Configuration path is not a file: {config_path}",
        )
        return ConfigLoadResult(
            config=None,
            issues=tuple(issues),
        )

    try:
        with config_path.open(
            "r",
            encoding="utf-8",
        ) as config_file:
            raw_config = yaml.safe_load(config_file)
    except OSError as error:
        _add_error(
            issues,
            "configuration",
            f"Could not read configuration: {error}",
        )
        return ConfigLoadResult(
            config=None,
            issues=tuple(issues),
        )
    except yaml.YAMLError as error:
        _add_error(
            issues,
            "configuration",
            f"Invalid YAML syntax: {error}",
        )
        return ConfigLoadResult(
            config=None,
            issues=tuple(issues),
        )

    if raw_config is None:
        raw_config = {}

    if not isinstance(raw_config, Mapping):
        _add_error(
            issues,
            "configuration",
            "The YAML root must be a mapping.",
        )
        return ConfigLoadResult(
            config=None,
            issues=tuple(issues),
        )

    _warn_unknown_keys(
        raw_config,
        ROOT_KEYS,
        "configuration",
        issues,
    )

    wallpaper_directory = _resolve_wallpaper_directory(
        raw_config.get("wallpaper_directory"),
        config_path,
        issues,
    )

    defaults, terminal_defaults = (
        _parse_defaults(
            raw_config.get("defaults"),
            "defaults",
            issues,
        )
    )

    raw_profiles = raw_config.get("profiles")

    if raw_profiles is None:
        _add_error(
            issues,
            "profiles",
            "Required field is missing.",
        )
        raw_profiles = []
    elif not isinstance(raw_profiles, list):
        _add_error(
            issues,
            "profiles",
            "Expected a list of profiles.",
        )
        raw_profiles = []

    profiles: list[Profile] = []
    profile_ids: set[str] = set()

    if wallpaper_directory is not None:
        for index, raw_profile in enumerate(raw_profiles):
            profile = _parse_profile(
                raw_profile,
                index,
                wallpaper_directory,
                profile_ids,
                issues,
            )

            if profile is not None:
                profiles.append(profile)

    wallpaper_owners: dict[Path, str] = {}

    for index, profile in enumerate(profiles):
        previous_profile = wallpaper_owners.get(
            profile.wallpaper
        )

        if previous_profile is not None:
            _add_error(
                issues,
                f"profiles[{index}].wallpaper",
                (
                    "Wallpaper is already assigned to profile "
                    f"{previous_profile!r}: {profile.wallpaper}"
                ),
            )
            continue

        wallpaper_owners[profile.wallpaper] = profile.id

    if not profiles:
        _add_error(
            issues,
            "profiles",
            "No valid profiles were found.",
        )

    if any(
        issue.level is IssueLevel.ERROR
        for issue in issues
    ):
        return ConfigLoadResult(
            config=None,
            issues=tuple(issues),
        )

    configuration = Configuration(
        source_path=config_path,
        wallpaper_directory=wallpaper_directory,
        defaults=defaults,
        profiles=tuple(profiles),
        terminal_defaults=terminal_defaults,
    )

    return ConfigLoadResult(
        config=configuration,
        issues=tuple(issues),
    )