"""Core data models used by Cinnameleon."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class IssueLevel(str, Enum):
    """Severity level of a configuration issue."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ConfigIssue:
    """A problem found while loading or validating configuration."""

    level: IssueLevel
    location: str
    message: str


@dataclass(frozen=True)
class ThemeVariants:
    """Dark and light variants of an appearance component."""

    dark: str | None = None
    light: str | None = None


@dataclass(frozen=True)
class FontSettings:
    """Fonts that can be configured by an appearance profile."""

    interface: str | None = None
    document: str | None = None
    monospace: str | None = None
    window_title: str | None = None


@dataclass(frozen=True)
class AppearanceSettings:
    """Appearance values shared by defaults and profiles."""

    gtk_theme: ThemeVariants = field(default_factory=ThemeVariants)
    cinnamon_theme: ThemeVariants = field(default_factory=ThemeVariants)
    window_borders: ThemeVariants = field(default_factory=ThemeVariants)
    icon_theme: ThemeVariants = field(default_factory=ThemeVariants)
    cursor_theme: ThemeVariants = field(default_factory=ThemeVariants)
    fonts: FontSettings = field(default_factory=FontSettings)


@dataclass(frozen=True)
class Profile:
    """A complete Cinnameleon appearance profile."""

    id: str
    name: str
    wallpaper: Path
    appearance: AppearanceSettings


@dataclass(frozen=True)
class Configuration:
    """Validated Cinnameleon configuration."""

    source_path: Path
    wallpaper_directory: Path
    defaults: AppearanceSettings
    profiles: tuple[Profile, ...]


@dataclass(frozen=True)
class ConfigLoadResult:
    """Result produced by the configuration loader."""

    config: Configuration | None
    issues: tuple[ConfigIssue, ...]

    @property
    def has_errors(self) -> bool:
        """Return whether at least one validation error exists."""

        return any(
            issue.level is IssueLevel.ERROR
            for issue in self.issues
        )

    @property
    def warnings(self) -> tuple[ConfigIssue, ...]:
        """Return all configuration warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.level is IssueLevel.WARNING
        )

    @property
    def errors(self) -> tuple[ConfigIssue, ...]:
        """Return all configuration errors."""

        return tuple(
            issue
            for issue in self.issues
            if issue.level is IssueLevel.ERROR
        )