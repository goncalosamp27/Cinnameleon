"""Terminal integrations for Cinnameleon."""

from __future__ import annotations

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gdk, Gio

from cinnameleon.models import (
    TerminalPalette,
)


PROFILES_LIST_SCHEMA = (
    "org.gnome.Terminal.ProfilesList"
)

PROFILE_SCHEMA = (
    "org.gnome.Terminal.Legacy.Profile"
)

PROFILE_PATH_PREFIX = (
    "/org/gnome/terminal/legacy/profiles:/"
)


DEFAULT_ANSI = (
    "#171421",
    "#C01C28",
    "#26A269",
    "#A2734C",
    "#12488B",
    "#A347BA",
    "#2AA1B3",
    "#D0CFCC",
    "#5E5C64",
    "#F66151",
    "#33D17A",
    "#E9AD0C",
    "#2A7BDE",
    "#C061CB",
    "#33C7DE",
    "#FFFFFF",
)


DEFAULT_TERMINAL_PALETTE = (
    TerminalPalette(
        background="#171421",
        foreground="#FFFFFF",
        cursor="#FFFFFF",
        selection_background="#FFFFFF",
        selection_foreground="#171421",
        ansi=DEFAULT_ANSI,
    )
)


class TerminalBackendError(
    RuntimeError
):
    """Raised when a terminal integration fails."""


def _normalize_color(
    value: str,
    fallback: str,
) -> str:
    rgba = Gdk.RGBA()

    try:
        parsed = rgba.parse(
            value
        )

    except Exception:
        parsed = False

    if not parsed:
        return fallback

    red = round(
        rgba.red * 255
    )

    green = round(
        rgba.green * 255
    )

    blue = round(
        rgba.blue * 255
    )

    return (
        f"#{red:02X}"
        f"{green:02X}"
        f"{blue:02X}"
    )


class GnomeTerminalBackend:
    """Read and apply the default GNOME Terminal profile palette."""

    def __init__(
        self,
    ) -> None:
        self._source = (
            Gio.SettingsSchemaSource
            .get_default()
        )

    def _schema(
        self,
        schema_id: str,
    ) -> Gio.SettingsSchema | None:
        if self._source is None:
            return None

        return self._source.lookup(
            schema_id,
            True,
        )

    def is_available(
        self,
    ) -> bool:
        return (
            self._schema(
                PROFILES_LIST_SCHEMA
            )
            is not None
            and self._schema(
                PROFILE_SCHEMA
            )
            is not None
        )

    def _profiles_settings(
        self,
    ) -> Gio.Settings:
        schema = self._schema(
            PROFILES_LIST_SCHEMA
        )

        if schema is None:
            raise TerminalBackendError(
                "GNOME Terminal profiles schema "
                "was not found."
            )

        return Gio.Settings.new_full(
            schema,
            None,
            None,
        )

    def default_profile_id(
        self,
    ) -> str:
        settings = (
            self._profiles_settings()
        )

        profile_id = (
            settings.get_string(
                "default"
            )
        )

        if profile_id:
            return profile_id

        profiles = settings.get_strv(
            "list"
        )

        if profiles:
            return profiles[0]

        raise TerminalBackendError(
            "GNOME Terminal has no profiles."
        )

    def _profile_schema(
        self,
    ) -> Gio.SettingsSchema:
        schema = self._schema(
            PROFILE_SCHEMA
        )

        if schema is None:
            raise TerminalBackendError(
                "GNOME Terminal profile schema "
                "was not found."
            )

        return schema

    def _profile_settings(
        self,
    ) -> Gio.Settings:
        profile_id = (
            self.default_profile_id()
        )

        path = (
            f"{PROFILE_PATH_PREFIX}"
            f":{profile_id}/"
        )

        return Gio.Settings.new_full(
            self._profile_schema(),
            None,
            path,
        )

    def _has_key(
        self,
        key: str,
    ) -> bool:
        return (
            self._profile_schema()
            .has_key(key)
        )

    def describe_target(
        self,
    ) -> str:
        if not self.is_available():
            return (
                "GNOME Terminal not detected"
            )

        try:
            profile_id = (
                self.default_profile_id()
            )

        except TerminalBackendError:
            return (
                "GNOME Terminal detected"
            )

        return (
            "GNOME Terminal · "
            f"{profile_id[:8]}"
        )

    def _read_color(
        self,
        settings: Gio.Settings,
        key: str,
        fallback: str,
    ) -> str:
        if not self._has_key(
            key
        ):
            return fallback

        value = settings.get_string(
            key
        )

        return _normalize_color(
            value,
            fallback,
        )

    def bold_is_bright(
        self,
    ) -> bool:
        """
        Return the actual bold-is-bright setting
        used by the default GNOME Terminal profile.
        """

        if not self.is_available():
            return True

        settings = (
            self._profile_settings()
        )

        if not self._has_key(
            "bold-is-bright"
        ):
            return True

        return settings.get_boolean(
            "bold-is-bright"
        )

    def read_palette(
        self,
    ) -> TerminalPalette:
        if not self.is_available():
            raise TerminalBackendError(
                "GNOME Terminal is not available."
            )

        settings = (
            self._profile_settings()
        )

        background = self._read_color(
            settings,
            "background-color",
            DEFAULT_TERMINAL_PALETTE.background,
        )

        foreground = self._read_color(
            settings,
            "foreground-color",
            DEFAULT_TERMINAL_PALETTE.foreground,
        )

        if (
            self._has_key(
                "cursor-colors-set"
            )
            and settings.get_boolean(
                "cursor-colors-set"
            )
        ):
            cursor = self._read_color(
                settings,
                "cursor-background-color",
                foreground,
            )

        else:
            cursor = foreground

        if (
            self._has_key(
                "highlight-colors-set"
            )
            and settings.get_boolean(
                "highlight-colors-set"
            )
        ):
            selection_background = (
                self._read_color(
                    settings,
                    "highlight-background-color",
                    foreground,
                )
            )

            selection_foreground = (
                self._read_color(
                    settings,
                    "highlight-foreground-color",
                    background,
                )
            )

        else:
            selection_background = (
                foreground
            )

            selection_foreground = (
                background
            )

        raw_palette = (
            settings.get_strv(
                "palette"
            )
            if self._has_key(
                "palette"
            )
            else ()
        )

        ansi: list[str] = []

        for index in range(16):
            fallback = DEFAULT_ANSI[
                index
            ]

            if index < len(
                raw_palette
            ):
                ansi.append(
                    _normalize_color(
                        raw_palette[
                            index
                        ],
                        fallback,
                    )
                )

            else:
                ansi.append(
                    fallback
                )

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

    def needs_apply(
        self,
        palette: TerminalPalette,
    ) -> bool:
        return (
            self.read_palette()
            != palette
        )

    @staticmethod
    def _set_string(
        settings: Gio.Settings,
        key: str,
        value: str,
    ) -> None:
        if not settings.set_string(
            key,
            value,
        ):
            raise TerminalBackendError(
                f"GNOME Terminal rejected {key}."
            )

    @staticmethod
    def _set_boolean(
        settings: Gio.Settings,
        key: str,
        value: bool,
    ) -> None:
        if not settings.set_boolean(
            key,
            value,
        ):
            raise TerminalBackendError(
                f"GNOME Terminal rejected {key}."
            )

    def apply_palette(
        self,
        palette: TerminalPalette,
    ) -> None:
        if not self.is_available():
            raise TerminalBackendError(
                "GNOME Terminal is not available."
            )

        settings = (
            self._profile_settings()
        )

        if self._has_key(
            "use-theme-colors"
        ):
            self._set_boolean(
                settings,
                "use-theme-colors",
                False,
            )

        self._set_string(
            settings,
            "background-color",
            palette.background,
        )

        self._set_string(
            settings,
            "foreground-color",
            palette.foreground,
        )

        if self._has_key(
            "palette"
        ):
            if not settings.set_strv(
                "palette",
                palette.ansi,
            ):
                raise TerminalBackendError(
                    "GNOME Terminal rejected "
                    "the ANSI palette."
                )

        if self._has_key(
            "cursor-colors-set"
        ):
            self._set_boolean(
                settings,
                "cursor-colors-set",
                True,
            )

        if self._has_key(
            "cursor-background-color"
        ):
            self._set_string(
                settings,
                "cursor-background-color",
                palette.cursor,
            )

        if self._has_key(
            "cursor-foreground-color"
        ):
            self._set_string(
                settings,
                "cursor-foreground-color",
                palette.background,
            )

        if self._has_key(
            "highlight-colors-set"
        ):
            self._set_boolean(
                settings,
                "highlight-colors-set",
                True,
            )

        if self._has_key(
            "highlight-background-color"
        ):
            self._set_string(
                settings,
                "highlight-background-color",
                palette.selection_background,
            )

        if self._has_key(
            "highlight-foreground-color"
        ):
            self._set_string(
                settings,
                "highlight-foreground-color",
                palette.selection_foreground,
            )

        Gio.Settings.sync()