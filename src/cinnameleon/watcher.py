"""Event-driven wallpaper monitoring for Cinnameleon."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gio, GLib

from cinnameleon.models import Configuration, Mode, Profile
from cinnameleon.resolver import resolve_profile
from cinnameleon.settings_backend import (
    BACKGROUND_SCHEMA,
    SettingsBackend,
    SettingsBackendError,
)
from cinnameleon.snapshot import (
    SnapshotError,
    SnapshotStore,
)


PICTURE_URI_KEY = "picture-uri"

MessageHandler = Callable[[str], None]


def wallpaper_path_from_uri(uri: str) -> Path | None:
    """Convert a local file URI into a canonical wallpaper path."""

    if not uri:
        return None

    wallpaper_file = Gio.File.new_for_uri(uri)
    local_path = wallpaper_file.get_path()

    if local_path is None:
        return None

    return Path(local_path).expanduser().resolve()


def build_wallpaper_index(
    configuration: Configuration,
) -> dict[Path, Profile]:
    """Build a constant-time wallpaper-to-profile lookup."""

    return {
        profile.wallpaper.resolve(): profile
        for profile in configuration.profiles
    }


class WallpaperWatcher:
    """Apply a profile whenever its wallpaper becomes active."""

    def __init__(
        self,
        configuration: Configuration,
        mode: Mode,
        *,
        backend: SettingsBackend | None = None,
        snapshot_store: SnapshotStore | None = None,
        on_message: MessageHandler = print,
    ) -> None:
        self._configuration = configuration
        self._mode = mode
        self._backend = backend or SettingsBackend()
        self._snapshot_store = snapshot_store or SnapshotStore()
        self._on_message = on_message

        self._profiles_by_wallpaper = build_wallpaper_index(
            configuration
        )

        self._background_settings = Gio.Settings.new(
            BACKGROUND_SCHEMA
        )

        self._signal_id: int | None = None
        self._loop: GLib.MainLoop | None = None
        self._processing = False
        self._last_wallpaper: Path | None = None

    def _emit(self, message: str) -> None:
        """Send a watcher status message."""

        self._on_message(message)

    def current_wallpaper(self) -> Path | None:
        """Read the current wallpaper from Cinnamon."""

        uri = self._background_settings.get_string(
            PICTURE_URI_KEY
        )

        return wallpaper_path_from_uri(uri)

    def _profile_for_wallpaper(
        self,
        wallpaper: Path,
    ) -> Profile | None:
        """Find a profile matching a canonical wallpaper path."""

        return self._profiles_by_wallpaper.get(
            wallpaper.resolve()
        )

    def synchronize_current_wallpaper(self) -> bool:
        """Apply the profile associated with the current wallpaper."""

        wallpaper = self.current_wallpaper()

        if wallpaper is None:
            self._emit(
                "Wallpaper has no supported local file path."
            )
            return False

        return self._synchronize_wallpaper(wallpaper)

    def _synchronize_wallpaper(
        self,
        wallpaper: Path,
    ) -> bool:
        """Synchronize appearance with one wallpaper path."""

        canonical_wallpaper = wallpaper.resolve()

        if self._processing:
            self._emit(
                "Wallpaper event ignored while another "
                "profile is being applied."
            )
            return False

        if canonical_wallpaper == self._last_wallpaper:
            return False

        self._last_wallpaper = canonical_wallpaper

        profile = self._profile_for_wallpaper(
            canonical_wallpaper
        )

        if profile is None:
            self._emit(
                "No profile matches wallpaper: "
                f"{canonical_wallpaper}"
            )
            return False

        effective_profile = resolve_profile(
            configuration=self._configuration,
            profile_id=profile.id,
            mode=self._mode,
        )

        self._processing = True

        try:
            changes = self._backend.plan_profile(
                effective_profile,
                include_cinnamon_theme=False,
            )

            required_changes = tuple(
                change
                for change in changes
                if change.requires_update
            )

            if not required_changes:
                self._emit(
                    f"Profile already active: {profile.name} "
                    f"({self._mode.value})"
                )
                return True

            snapshot = self._backend.capture_snapshot()
            snapshot_path = self._snapshot_store.save(snapshot)

            self._backend.apply_changes(required_changes)

            self._emit(
                f"Applied profile: {profile.name} "
                f"({self._mode.value})"
            )
            self._emit(
                f"Safety snapshot: {snapshot_path}"
            )

            return True

        except (SettingsBackendError, SnapshotError) as error:
            self._emit(
                f"Could not apply profile {profile.name!r}: "
                f"{error}"
            )
            return False

        finally:
            self._processing = False

    def _on_picture_uri_changed(
        self,
        _: Gio.Settings,
        key: str,
    ) -> None:
        """Handle a Cinnamon wallpaper change event."""

        if key != PICTURE_URI_KEY:
            return

        wallpaper = self.current_wallpaper()

        if wallpaper is None:
            self._emit(
                "Wallpaper changed, but its URI is not "
                "a supported local file."
            )
            return

        self._emit(f"Wallpaper changed: {wallpaper}")
        self._synchronize_wallpaper(wallpaper)

    def start(
        self,
        *,
        synchronize_initial: bool = True,
    ) -> None:
        """Start listening to wallpaper changes."""

        if self._loop is not None:
            raise RuntimeError(
                "Wallpaper watcher is already running."
            )

        self._signal_id = self._background_settings.connect(
            f"changed::{PICTURE_URI_KEY}",
            self._on_picture_uri_changed,
        )

        # Gio.Settings only emits the detailed changed signal
        # reliably after the key has been read while connected.
        initial_wallpaper = self.current_wallpaper()

        self._loop = GLib.MainLoop()

        self._emit("Wallpaper watcher started.")
        self._emit(f"Mode: {self._mode.value}")

        if initial_wallpaper is not None:
            self._emit(
                f"Current wallpaper: {initial_wallpaper}"
            )

        if synchronize_initial:
            self.synchronize_current_wallpaper()

        try:
            self._loop.run()
        except KeyboardInterrupt:
            self._emit("Wallpaper watcher interrupted.")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the watcher and disconnect its signal."""

        if self._signal_id is not None:
            self._background_settings.disconnect(
                self._signal_id
            )
            self._signal_id = None

        if self._loop is not None:
            if self._loop.is_running():
                self._loop.quit()

            self._loop = None
