from __future__ import annotations

from pathlib import Path

import yaml

from cinnameleon.config_editor import (
    save_profile_edits,
)
from cinnameleon.models import (
    AppearanceSettings,
    Configuration,
    EffectiveAppearance,
    EffectiveProfile,
    FontSettings,
    Mode,
    Profile,
    ThemeVariants,
)


def test_save_only_writes_actual_overrides(
    tmp_path: Path,
) -> None:
    config_path = (
        tmp_path / "config.yaml"
    )

    config_path.write_text(
        """
# This comment must survive.

wallpaper_directory: /tmp

defaults:
  gtk_theme:
    dark: Default-GTK-Dark
    light: Default-GTK-Light

  icon_theme:
    dark: Default-Icons
    light: Default-Icons-Light

profiles:
  - id: gengar
    name: Gengar
    wallpaper: gengar.png
""".lstrip(),
        encoding="utf-8",
    )

    profile = Profile(
        id="gengar",
        name="Gengar",
        wallpaper=Path(
            "/tmp/gengar.png"
        ),
        appearance=(
            AppearanceSettings()
        ),
    )

    configuration = Configuration(
        source_path=config_path,
        wallpaper_directory=Path(
            "/tmp"
        ),
        defaults=AppearanceSettings(
            gtk_theme=ThemeVariants(
                dark="Default-GTK-Dark",
                light="Default-GTK-Light",
            ),
            icon_theme=ThemeVariants(
                dark="Default-Icons",
                light="Default-Icons-Light",
            ),
        ),
        profiles=(
            profile,
        ),
    )

    desired = EffectiveProfile(
        id="gengar",
        name="Gengar Purple",
        mode=Mode.DARK,
        wallpaper=Path(
            "/tmp/gengar.png"
        ),
        appearance=EffectiveAppearance(
            # Still inherited from defaults.
            # This must NOT be copied into the profile.
            gtk_theme="Default-GTK-Dark",

            # Changed in GUI.
            icon_theme="Purple-Icons",

            fonts=FontSettings(),
        ),
    )

    changed = save_profile_edits(
        configuration,
        desired,
    )

    assert changed

    text = config_path.read_text(
        encoding="utf-8"
    )

    assert (
        "# This comment must survive."
        in text
    )

    data = yaml.safe_load(
        text
    )

    saved_profile = (
        data["profiles"][0]
    )

    assert (
        saved_profile["name"]
        == "Gengar Purple"
    )

    assert (
        "gtk_theme"
        not in saved_profile
    )

    assert (
        saved_profile[
            "icon_theme"
        ]["dark"]
        == "Purple-Icons"
    )