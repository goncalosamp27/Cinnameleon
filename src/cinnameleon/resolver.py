"""Resolve profile overrides, defaults and global appearance mode."""

from __future__ import annotations

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


class ProfileNotFoundError(LookupError):
    """Raised when a requested profile does not exist."""

    def __init__(self, profile_id: str) -> None:
        super().__init__(f"Profile was not found: {profile_id}")
        self.profile_id = profile_id


def find_profile(
    configuration: Configuration,
    profile_id: str,
) -> Profile:
    """Find a profile by its unique identifier."""

    for profile in configuration.profiles:
        if profile.id == profile_id:
            return profile

    raise ProfileNotFoundError(profile_id)


def _variant_for_mode(
    variants: ThemeVariants,
    mode: Mode,
) -> str | None:
    """Return the dark or light value from a variant pair."""

    if mode is Mode.DARK:
        return variants.dark

    return variants.light


def _resolve_variant(
    profile_variants: ThemeVariants,
    default_variants: ThemeVariants,
    mode: Mode,
) -> str | None:
    """Resolve one theme value using profile-first precedence."""

    profile_value = _variant_for_mode(
        profile_variants,
        mode,
    )

    if profile_value is not None:
        return profile_value

    return _variant_for_mode(
        default_variants,
        mode,
    )


def _resolve_value(
    profile_value: str | None,
    default_value: str | None,
) -> str | None:
    """Resolve a non-mode-specific value."""

    if profile_value is not None:
        return profile_value

    return default_value


def _resolve_fonts(
    profile: FontSettings,
    defaults: FontSettings,
) -> FontSettings:
    """Resolve profile fonts using defaults as fallback."""

    return FontSettings(
        interface=_resolve_value(
            profile.interface,
            defaults.interface,
        ),
        document=_resolve_value(
            profile.document,
            defaults.document,
        ),
        monospace=_resolve_value(
            profile.monospace,
            defaults.monospace,
        ),
        window_title=_resolve_value(
            profile.window_title,
            defaults.window_title,
        ),
    )


def resolve_appearance(
    profile: AppearanceSettings,
    defaults: AppearanceSettings,
    mode: Mode,
) -> EffectiveAppearance:
    """Resolve the final appearance for one profile and mode."""

    return EffectiveAppearance(
        gtk_theme=_resolve_variant(
            profile.gtk_theme,
            defaults.gtk_theme,
            mode,
        ),
        cinnamon_theme=_resolve_variant(
            profile.cinnamon_theme,
            defaults.cinnamon_theme,
            mode,
        ),
        window_borders=_resolve_variant(
            profile.window_borders,
            defaults.window_borders,
            mode,
        ),
        icon_theme=_resolve_variant(
            profile.icon_theme,
            defaults.icon_theme,
            mode,
        ),
        cursor_theme=_resolve_variant(
            profile.cursor_theme,
            defaults.cursor_theme,
            mode,
        ),
        fonts=_resolve_fonts(
            profile.fonts,
            defaults.fonts,
        ),
    )


def resolve_profile(
    configuration: Configuration,
    profile_id: str,
    mode: Mode,
) -> EffectiveProfile:
    """Resolve a configured profile for the selected mode."""

    profile = find_profile(
        configuration,
        profile_id,
    )

    appearance = resolve_appearance(
        profile=profile.appearance,
        defaults=configuration.defaults,
        mode=mode,
    )

    return EffectiveProfile(
        id=profile.id,
        name=profile.name,
        mode=mode,
        wallpaper=profile.wallpaper,
        appearance=appearance,
    )