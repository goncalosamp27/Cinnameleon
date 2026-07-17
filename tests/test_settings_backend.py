"""Tests for effective-profile to GSettings mapping."""

from __future__ import annotations

import unittest
from pathlib import Path

from cinnameleon.models import (
    EffectiveAppearance,
    EffectiveProfile,
    FontSettings,
    Mode,
)
from cinnameleon.settings_backend import (
    BACKGROUND_SCHEMA,
    INTERFACE_SCHEMA,
    build_setting_targets,
)


class SettingTargetTests(unittest.TestCase):
    """Verify GSettings target generation."""

    def test_wallpaper_is_always_last(self) -> None:
        profile = EffectiveProfile(
            id="test",
            name="Test",
            mode=Mode.DARK,
            wallpaper=Path("/tmp/wallpaper.png"),
            appearance=EffectiveAppearance(
                gtk_theme="Mint-Y-Dark",
            ),
        )

        targets = build_setting_targets(profile)

        self.assertEqual(
            targets[-1].schema_id,
            BACKGROUND_SCHEMA,
        )
        self.assertEqual(
            targets[-1].key,
            "picture-uri",
        )
        self.assertEqual(
            targets[-1].value,
            "file:///tmp/wallpaper.png",
        )

    def test_missing_values_are_not_mapped(self) -> None:
        profile = EffectiveProfile(
            id="test",
            name="Test",
            mode=Mode.DARK,
            wallpaper=Path("/tmp/wallpaper.png"),
            appearance=EffectiveAppearance(),
        )

        targets = build_setting_targets(profile)

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].label, "Wallpaper")

    def test_interface_values_use_cinnamon_schema(self) -> None:
        profile = EffectiveProfile(
            id="test",
            name="Test",
            mode=Mode.DARK,
            wallpaper=Path("/tmp/wallpaper.png"),
            appearance=EffectiveAppearance(
                gtk_theme="GTK Test",
                icon_theme="Icons Test",
                cursor_theme="Cursor Test",
                fonts=FontSettings(
                    interface="Interface Test 10",
                ),
            ),
        )

        targets = build_setting_targets(profile)

        interface_targets = {
            target.key: target.value
            for target in targets
            if target.schema_id == INTERFACE_SCHEMA
        }

        self.assertEqual(
            interface_targets,
            {
                "gtk-theme": "GTK Test",
                "icon-theme": "Icons Test",
                "cursor-theme": "Cursor Test",
                "font-name": "Interface Test 10",
            },
        )

    def test_cinnamon_theme_is_skipped_by_default(self) -> None:
        profile = EffectiveProfile(
            id="test",
            name="Test",
            mode=Mode.DARK,
            wallpaper=Path("/tmp/wallpaper.png"),
            appearance=EffectiveAppearance(
                cinnamon_theme="Mint-Y",
            ),
        )

        targets = build_setting_targets(profile)

        cinnamon_targets = [
            target
            for target in targets
            if target.schema_id == "org.cinnamon.theme"
        ]

        self.assertEqual(cinnamon_targets, [])


    def test_cinnamon_theme_can_be_explicitly_included(
        self,
    ) -> None:
        profile = EffectiveProfile(
            id="test",
            name="Test",
            mode=Mode.DARK,
            wallpaper=Path("/tmp/wallpaper.png"),
            appearance=EffectiveAppearance(
                cinnamon_theme="Mint-Y",
            ),
        )

        targets = build_setting_targets(
            profile,
            include_cinnamon_theme=True,
        )

        cinnamon_targets = [
            target
            for target in targets
            if target.schema_id == "org.cinnamon.theme"
        ]

        self.assertEqual(len(cinnamon_targets), 1)
        self.assertEqual(
            cinnamon_targets[0].value,
            "Mint-Y",
        )


if __name__ == "__main__":
    unittest.main()
