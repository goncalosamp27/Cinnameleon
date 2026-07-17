"""Tests for wallpaper matching helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from cinnameleon.models import (
    AppearanceSettings,
    Configuration,
    Profile,
)
from cinnameleon.watcher import (
    build_wallpaper_index,
    wallpaper_path_from_uri,
)


class WallpaperWatcherHelperTests(unittest.TestCase):
    """Verify wallpaper URI conversion and profile indexing."""

    def test_local_file_uri_is_converted_to_path(self) -> None:
        path = wallpaper_path_from_uri(
            "file:///tmp/My%20Wallpaper.png"
        )

        self.assertEqual(
            path,
            Path("/tmp/My Wallpaper.png"),
        )

    def test_non_local_uri_has_no_path(self) -> None:
        path = wallpaper_path_from_uri(
            "https://example.com/wallpaper.png"
        )

        self.assertIsNone(path)

    def test_profiles_are_indexed_by_wallpaper(self) -> None:
        profile = Profile(
            id="test",
            name="Test",
            wallpaper=Path("/tmp/wallpaper.png"),
            appearance=AppearanceSettings(),
        )

        configuration = Configuration(
            source_path=Path("/tmp/config.yaml"),
            wallpaper_directory=Path("/tmp"),
            defaults=AppearanceSettings(),
            profiles=(profile,),
        )

        index = build_wallpaper_index(configuration)

        self.assertIs(
            index[Path("/tmp/wallpaper.png")],
            profile,
        )


if __name__ == "__main__":
    unittest.main()
