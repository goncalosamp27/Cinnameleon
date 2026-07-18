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
StateHandler = Callable[[Profile | None, Mode], None]


def wallpaper_path_from_uri(uri: str) -> Path | None:
    """Convert a local file URI into a canonical path."""

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
        on_state_changed: StateHandler | None = None,
    ) -> None:
        self._configuration = configuration
        self._mode = mode
        self._backend = backend or SettingsBackend()
        self._snapshot_store = snapshot_store or SnapshotStore()
        self._on_message = on_message
        self._on_state_changed = on_state_changed

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

    def _notify_state(
        self,
        profile: Profile | None,
    ) -> None:
        """Notify the application about the active profile."""

        if self._on_state_changed is not None:
            self._on_state_changed(
                profile,
                self._mode,
            )

    @property
    def is_listening(self) -> bool:
        """Return whether the GSettings signal is connected."""

        return self._signal_id is not None

    def current_wallpaper(self) -> Path | None:
        """Read the current wallpaper from Cinnamon."""

        uri = self._background_settings.get_string(
            PICTURE_URI_KEY
        )

        return wallpaper_path_from_uri(uri)

    def update_configuration(
        self,
        configuration: Configuration,
        *,
        synchronize_current: bool = True,
    ) -> None:
        """Replace the active configuration without restarting."""

        self._configuration = configuration
        self._profiles_by_wallpaper = build_wallpaper_index(
            configuration
        )

        # Force re-evaluation because the profile definition may
        # have changed while the wallpaper stayed the same.
        self._last_wallpaper = None

        self._emit(
            "Configuration updated: "
            f"{len(configuration.profiles)} profile(s)"
        )

        if synchronize_current:
            self.synchronize_current_wallpaper()

    def set_mode(
        self,
        mode: Mode,
        *,
        synchronize_current: bool = True,
    ) -> None:
        """Change the global appearance mode."""

        if mode is self._mode:
            return

        self._mode = mode
        self._last_wallpaper = None

        self._emit(f"Mode changed: {mode.value}")

        if synchronize_current:
            self.synchronize_current_wallpaper()

    def _profile_for_wallpaper(
        self,
        wallpaper: Path,
    ) -> Profile | None:
        """Find a profile matching a wallpaper path."""

        return self._profiles_by_wallpaper.get(
            wallpaper.resolve()
        )
    
    def apply_profile(self, profile_id: str) -> bool:
        """Manually select and apply a configured profile."""

        profile = next(
            (
                configured_profile
                for configured_profile
                in self._configuration.profiles
                if configured_profile.id == profile_id
            ),
            None,
        )

        if profile is None:
            self._emit(
                f"Profile was not found: {profile_id}"
            )
            return False

        # Prevent the wallpaper event generated by this operation
        # from applying the same profile a second time.
        self._last_wallpaper = profile.wallpaper.resolve()

        return self._apply_profile(profile)

    def synchronize_current_wallpaper(self) -> bool:
        """Apply the profile associated with the current wallpaper."""

        wallpaper = self.current_wallpaper()

        if wallpaper is None:
            self._emit(
                "Wallpaper has no supported local file path."
            )
            self._notify_state(None)
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
            self._notify_state(None)
            return False

        return self._apply_profile(profile)

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
            self._notify_state(None)
            return

        self._emit(f"Wallpaper changed: {wallpaper}")
        self._synchronize_wallpaper(wallpaper)

    def start_listening(
        self,
        *,
        synchronize_initial: bool = True,
    ) -> None:
        """Connect the wallpaper signal without starting a loop."""

        if self._signal_id is not None:
            raise RuntimeError(
                "Wallpaper watcher is already listening."
            )

        self._signal_id = self._background_settings.connect(
            f"changed::{PICTURE_URI_KEY}",
            self._on_picture_uri_changed,
        )

        initial_wallpaper = self.current_wallpaper()

        self._emit("Wallpaper watcher started.")
        self._emit(f"Mode: {self._mode.value}")

        if initial_wallpaper is not None:
            self._emit(
                f"Current wallpaper: {initial_wallpaper}"
            )

        if synchronize_initial:
            self.synchronize_current_wallpaper()

    def stop_listening(self) -> None:
        """Disconnect the wallpaper signal."""

        if self._signal_id is None:
            return

        self._background_settings.disconnect(
            self._signal_id
        )
        self._signal_id = None

        self._emit("Wallpaper watcher stopped.")

    def start(
        self,
        *,
        synchronize_initial: bool = True,
    ) -> None:
        """Run the standalone command-line watcher."""

        if self._loop is not None:
            raise RuntimeError(
                "Wallpaper watcher is already running."
            )

        self.start_listening(
            synchronize_initial=synchronize_initial
        )

        self._loop = GLib.MainLoop()

        try:
            self._loop.run()
        except KeyboardInterrupt:
            self._emit("Wallpaper watcher interrupted.")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the standalone loop and disconnect signals."""

        self.stop_listening()

        if self._loop is not None:
            if self._loop.is_running():
                self._loop.quit()

            self._loop = None

    def _apply_profile(
        self,
        profile: Profile,
    ) -> bool:
        """Resolve and apply one profile using the current mode."""

        if self._processing:
            self._emit(
                "Profile selection ignored while another "
                "profile is being applied."
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
                self._notify_state(profile)
                return True

            snapshot = self._backend.capture_snapshot()
            snapshot_path = self._snapshot_store.save(
                snapshot
            )

            self._backend.apply_changes(required_changes)

            self._emit(
                f"Applied profile: {profile.name} "
                f"({self._mode.value})"
            )
            self._emit(
                f"Safety snapshot: {snapshot_path}"
            )

            self._notify_state(profile)

            return True

        except (SettingsBackendError, SnapshotError) as error:
            # Allow another attempt even if the wallpaper
            # itself did not change again.
            self._last_wallpaper = None

            self._emit(
                f"Could not apply profile {profile.name!r}: "
                f"{error}"
            )
            return False

        finally:
            self._processing = False