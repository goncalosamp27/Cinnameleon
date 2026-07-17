"""Tests for profile and default resolution."""

from __future__ import annotations

import unittest
from pathlib import Path

from cinnameleon.models import (
    AppearanceSettings,
    Configuration,
    FontSettings,
    Mode,
    Profile,
    ThemeVariants,
)
from cinnameleon.resolver import (
    ProfileNotFoundError,
    resolve_profile,
)


class ProfileResolverTests(unittest.TestCase):
    """Verify profile-first fallback resolution."""

    def setUp(self) -> None:
        defaults = AppearanceSettings(
            gtk_theme=ThemeVariants(
                dark="Default GTK Dark",
                light="Default GTK Light",
            ),
            cinnamon_theme=ThemeVariants(
                dark="Default Cinnamon Dark",
                light="Default Cinnamon Light",
            ),
            icon_theme=ThemeVariants(
                dark="Default Icons Dark",
                light="Default Icons Light",
            ),
            fonts=FontSettings(
                interface="Default Sans 10",
                monospace="Default Mono 10",
            ),
        )

        profile = Profile(
            id="test",
            name="Test profile",
            wallpaper=Path("/tmp/wallpaper.png"),
            appearance=AppearanceSettings(
                gtk_theme=ThemeVariants(
                    dark="Profile GTK Dark",
                ),
                icon_theme=ThemeVariants(
                    light="Profile Icons Light",
                ),
                fonts=FontSettings(
                    interface="Profile Sans 11",
                ),
            ),
        )

        self.configuration = Configuration(
            source_path=Path("/tmp/config.yaml"),
            wallpaper_directory=Path("/tmp"),
            defaults=defaults,
            profiles=(profile,),
        )

    def test_profile_value_overrides_default(self) -> None:
        resolved = resolve_profile(
            self.configuration,
            "test",
            Mode.DARK,
        )

        self.assertEqual(
            resolved.appearance.gtk_theme,
            "Profile GTK Dark",
        )

    def test_missing_profile_value_uses_default(self) -> None:
        resolved = resolve_profile(
            self.configuration,
            "test",
            Mode.DARK,
        )

        self.assertEqual(
            resolved.appearance.icon_theme,
            "Default Icons Dark",
        )

    def test_resolution_uses_selected_mode(self) -> None:
        resolved = resolve_profile(
            self.configuration,
            "test",
            Mode.LIGHT,
        )

        self.assertEqual(
            resolved.appearance.gtk_theme,
            "Default GTK Light",
        )
        self.assertEqual(
            resolved.appearance.icon_theme,
            "Profile Icons Light",
        )

    def test_profile_font_overrides_default(self) -> None:
        resolved = resolve_profile(
            self.configuration,
            "test",
            Mode.DARK,
        )

        self.assertEqual(
            resolved.appearance.fonts.interface,
            "Profile Sans 11",
        )
        self.assertEqual(
            resolved.appearance.fonts.monospace,
            "Default Mono 10",
        )

    def test_missing_profile_raises_error(self) -> None:
        with self.assertRaises(ProfileNotFoundError):
            resolve_profile(
                self.configuration,
                "missing",
                Mode.DARK,
            )


if __name__ == "__main__":
    unittest.main()
