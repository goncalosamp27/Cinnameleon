"""Resident single-instance Cinnameleon application."""

from __future__ import annotations

import signal
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GLib, Gtk

from cinnameleon.config import (
    load_configuration,
)
from cinnameleon.logging_setup import (
    configure_logging,
)
from cinnameleon.main_window import MainWindow
from cinnameleon.models import (
    ConfigIssue,
    Configuration,
    EffectiveProfile,
    IssueLevel,
    Mode,
    Profile,
)
from cinnameleon.state import (
    ApplicationState,
    StateError,
    StateStore,
)
from cinnameleon.tray import TrayIcon
from cinnameleon.validator import (
    validate_configuration_resources,
)
from cinnameleon.watcher import (
    WallpaperWatcher,
)
from cinnameleon.config_editor import (
    ConfigEditError,
    change_profile_wallpaper,
    create_profile,
    delete_profile,
    duplicate_profile,
    save_profile_edits,
)


APPLICATION_ID = (
    "io.github.goncalosamp27.cinnameleon"
)

RELOAD_DELAY_MS = 300


class CinnameleonApplication(
    Gtk.Application
):
    """Single-instance resident application."""

    def __init__(
        self,
        *,
        config_path: Path,
        mode: Mode,
        synchronize_initial: bool = True,
        show_window: bool = False,
        verbose: bool = False,
    ) -> None:
        super().__init__(
            application_id=APPLICATION_ID,
            flags=(
                Gio.ApplicationFlags
                .FLAGS_NONE
            ),
        )

        self._config_path = (
            config_path.resolve()
        )

        self._mode = mode

        self._synchronize_initial = (
            synchronize_initial
        )

        self._show_window_on_activate = (
            show_window
        )

        self._logger = configure_logging(
            console=True,
            verbose=verbose,
        )

        self._configuration: (
            Configuration | None
        ) = None

        self._current_profile: (
            Profile | None
        ) = None

        self._watcher: (
            WallpaperWatcher | None
        ) = None

        self._config_monitor: (
            Gio.FileMonitor | None
        ) = None

        self._tray: TrayIcon | None = None

        self._main_window: (
            MainWindow | None
        ) = None

        self._reload_source_id: (
            int | None
        ) = None

        self._signal_source_ids: (
            list[int]
        ) = []

        self._held = False

        self._state_store = (
            StateStore()
        )

    def do_startup(
        self,
    ) -> None:
        Gtk.Application.do_startup(
            self
        )

        self.hold()
        self._held = True

        self._install_unix_signal_handlers()

        self._tray = TrayIcon(
            config_path=self._config_path,
            on_open_window=(
                self.show_main_window
            ),
            on_profile_selected=(
                self._on_tray_profile_selected
            ),
            on_mode_changed=(
                self._on_tray_mode_changed
            ),
            on_reload=(
                self._on_tray_reload
            ),
            on_open_config=(
                self._open_config_folder
            ),
            on_quit=self.quit,
        )

        self._start_config_monitor()

        self._reload_configuration(
            initial=True
        )

    def do_activate(
        self,
    ) -> None:
        self._logger.debug(
            "Application activated"
        )

        if self._show_window_on_activate:
            self.show_main_window()

    def show_main_window(
        self,
    ) -> None:
        """Create or present the GUI."""

        if self._configuration is None:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=(
                    Gtk.DialogFlags.MODAL
                ),
                message_type=(
                    Gtk.MessageType.ERROR
                ),
                buttons=(
                    Gtk.ButtonsType.CLOSE
                ),
                text=(
                    "Cinnameleon configuration "
                    "is invalid"
                ),
            )

            dialog.format_secondary_text(
                "Fix config.yaml and reload "
                "the configuration first."
            )

            dialog.run()
            dialog.destroy()

            return

        if self._main_window is None:
            self._main_window = MainWindow(
                application=self,
                configuration=self._configuration,
                mode=self._mode,
                current_profile=self._current_profile,
                on_apply=self._apply_window_profile,
                on_save=self._save_window_profile,
                on_new_profile=self._create_window_profile,
                on_duplicate_profile=(
                    self._duplicate_window_profile
                ),
                on_delete_profile=(
                    self._delete_window_profile
                ),
                on_change_wallpaper=(
                    self._change_window_wallpaper
                ),
            )

        self._main_window.show_all()
        self._main_window.present()

    def _refresh_tray(
        self,
        *,
        config_valid: bool = True,
    ) -> None:
        if self._tray is None:
            return

        profiles = (
            self._configuration.profiles
            if self._configuration
            is not None
            else ()
        )

        self._tray.update_status(
            profiles=profiles,
            current_profile=(
                self._current_profile
            ),
            mode=self._mode,
            config_valid=config_valid,
        )

    def _on_tray_profile_selected(
        self,
        profile_id: str,
    ) -> None:
        if self._watcher is None:
            self._logger.warning(
                "Profile selection ignored: "
                "watcher is unavailable"
            )

            return

        self._logger.info(
            "Profile selected from tray: %s",
            profile_id,
        )

        self._watcher.apply_profile(
            profile_id
        )

    def _save_runtime_state(
        self,
    ) -> None:
        try:
            state_path = (
                self._state_store.save(
                    ApplicationState(
                        mode=self._mode
                    )
                )
            )

        except StateError as error:
            self._logger.warning(
                "Could not save "
                "application state: %s",
                error,
            )

            return

        self._logger.debug(
            "Application state saved: %s",
            state_path,
        )

    def _on_tray_mode_changed(
        self,
        mode: Mode,
    ) -> None:
        if mode is self._mode:
            return

        self._logger.info(
            "Mode selected from tray: %s",
            mode.value,
        )

        self._mode = mode

        self._save_runtime_state()

        if self._watcher is None:
            self._refresh_tray()
            return

        self._watcher.set_mode(
            mode,
            synchronize_current=True,
        )

    def _create_window_profile(
        self,
        name: str,
        wallpaper: Path,
    ) -> str | None:
        """Create a profile from the GUI."""

        if self._configuration is None:
            return None

        try:
            profile_id = create_profile(
                self._configuration,
                name=name,
                wallpaper=wallpaper,
            )

        except ConfigEditError as error:
            self._logger.error(
                "Could not create profile: %s",
                error,
            )

            return None

        if not self._reload_configuration(
            initial=False
        ):
            return None

        self._logger.info(
            "Profile created: %s",
            profile_id,
        )

        return profile_id

    def _duplicate_window_profile(
        self,
        profile_id: str,
    ) -> str | None:
        """Duplicate a profile from the GUI."""

        if self._configuration is None:
            return None

        try:
            new_id = duplicate_profile(
                self._configuration,
                profile_id,
            )

        except ConfigEditError as error:
            self._logger.error(
                "Could not duplicate profile %s: %s",
                profile_id,
                error,
            )

            return None

        if not self._reload_configuration(
            initial=False
        ):
            return None

        self._logger.info(
            "Profile duplicated: %s -> %s",
            profile_id,
            new_id,
        )

        return new_id

    def _delete_window_profile(
        self,
        profile_id: str,
    ) -> bool:
        """Delete a profile from the GUI."""

        if self._configuration is None:
            return False

        try:
            delete_profile(
                self._configuration,
                profile_id,
            )

        except ConfigEditError as error:
            self._logger.error(
                "Could not delete profile %s: %s",
                profile_id,
                error,
            )

            return False

        self._logger.info(
            "Profile deleted: %s",
            profile_id,
        )

        return self._reload_configuration(
            initial=False
        )

    def _change_window_wallpaper(
        self,
        profile_id: str,
        wallpaper: Path,
    ) -> bool:
        """Import a new wallpaper from the GUI."""

        if self._configuration is None:
            return False

        try:
            changed = (
                change_profile_wallpaper(
                    self._configuration,
                    profile_id,
                    wallpaper,
                )
            )

        except ConfigEditError as error:
            self._logger.error(
                "Could not change wallpaper "
                "for %s: %s",
                profile_id,
                error,
            )

            return False

        if not changed:
            return True

        self._logger.info(
            "Wallpaper changed for profile: %s",
            profile_id,
        )

        return self._reload_configuration(
            initial=False
        )

    def _save_window_profile(
        self,
        effective_profile: EffectiveProfile,
    ) -> bool:
        """Persist changes made in the graphical editor."""

        if self._configuration is None:
            return False

        try:
            changed = save_profile_edits(
                self._configuration,
                effective_profile,
            )

        except ConfigEditError as error:
            self._logger.error(
                "Could not save profile %s: %s",
                effective_profile.id,
                error,
            )

            return False

        if not changed:
            self._logger.info(
                "Profile has no changes to save: %s",
                effective_profile.id,
            )

            return True

        self._logger.info(
            "Profile saved: %s",
            effective_profile.id,
        )

        # Reload immediately rather than waiting for
        # Gio.FileMonitor's debounce.

        return self._reload_configuration(
            initial=False
        )

    def _apply_window_profile(
        self,
        effective_profile: EffectiveProfile,
    ) -> bool:
        """Apply temporary GUI values."""

        if (
            self._watcher is None
            or self._configuration is None
        ):
            return False

        profile = next(
            (
                item
                for item
                in self._configuration.profiles
                if item.id
                == effective_profile.id
            ),
            None,
        )

        if profile is None:
            self._logger.error(
                "Profile does not exist: %s",
                effective_profile.id,
            )

            return False

        if (
            effective_profile.mode
            is not self._mode
        ):
            self._mode = (
                effective_profile.mode
            )

            self._save_runtime_state()

            self._watcher.set_mode(
                self._mode,
                synchronize_current=False,
            )

        return (
            self._watcher
            .apply_effective_profile(
                profile,
                effective_profile,
            )
        )

    def _on_tray_reload(
        self,
    ) -> None:
        self._logger.info(
            "Manual configuration "
            "reload requested"
        )

        self._reload_configuration(
            initial=False
        )

    def _open_config_folder(
        self,
    ) -> None:
        uri = (
            self._config_path
            .parent
            .as_uri()
        )

        try:
            Gio.AppInfo.launch_default_for_uri(
                uri,
                None,
            )

        except GLib.Error as error:
            self._logger.error(
                "Could not open "
                "configuration folder: %s",
                error,
            )

    def _on_profile_state_changed(
        self,
        profile: Profile | None,
        mode: Mode,
    ) -> None:
        self._current_profile = profile
        self._mode = mode

        self._refresh_tray(
            config_valid=True
        )

        if self._main_window is not None:
            self._main_window.set_active_state(
                profile,
                mode,
            )

    def _install_unix_signal_handlers(
        self,
    ) -> None:
        for signal_number in (
            signal.SIGINT,
            signal.SIGTERM,
        ):
            source_id = (
                GLib.unix_signal_add(
                    GLib.PRIORITY_DEFAULT,
                    signal_number,
                    self._on_unix_signal,
                )
            )

            self._signal_source_ids.append(
                source_id
            )

    def _on_unix_signal(
        self,
    ) -> bool:
        self._logger.info(
            "Termination signal received"
        )

        self.quit()

        return GLib.SOURCE_REMOVE

    def _start_config_monitor(
        self,
    ) -> None:
        self._config_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        config_directory = (
            Gio.File.new_for_path(
                str(
                    self._config_path.parent
                )
            )
        )

        try:
            self._config_monitor = (
                config_directory
                .monitor_directory(
                    Gio.FileMonitorFlags
                    .WATCH_MOVES,
                    None,
                )
            )

        except GLib.Error as error:
            self._logger.error(
                "Could not monitor "
                "configuration: %s",
                error,
            )

            return

        self._config_monitor.connect(
            "changed",
            self._on_config_directory_changed,
        )

        self._logger.info(
            "Monitoring configuration changes"
        )

    def _file_matches_config(
        self,
        file: Gio.File | None,
    ) -> bool:
        if file is None:
            return False

        file_path = file.get_path()

        if file_path is None:
            return False

        return (
            Path(file_path).resolve()
            == self._config_path
        )

    def _on_config_directory_changed(
        self,
        _: Gio.FileMonitor,
        file: Gio.File,
        other_file: Gio.File | None,
        event_type: Gio.FileMonitorEvent,
    ) -> None:
        if not (
            self._file_matches_config(
                file
            )
            or self._file_matches_config(
                other_file
            )
        ):
            return

        relevant_events = {
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.MOVED_IN,
            Gio.FileMonitorEvent.RENAMED,
        }

        if (
            event_type
            not in relevant_events
        ):
            return

        if (
            self._reload_source_id
            is not None
        ):
            GLib.source_remove(
                self._reload_source_id
            )

        self._reload_source_id = (
            GLib.timeout_add(
                RELOAD_DELAY_MS,
                self._perform_scheduled_reload,
            )
        )

    def _perform_scheduled_reload(
        self,
    ) -> bool:
        self._reload_source_id = None

        self._reload_configuration(
            initial=False
        )

        return GLib.SOURCE_REMOVE

    def _load_validated_configuration(
        self,
    ) -> tuple[
        Configuration | None,
        tuple[ConfigIssue, ...],
    ]:
        result = load_configuration(
            self._config_path
        )

        issues = list(
            result.issues
        )

        if result.config is not None:
            issues.extend(
                validate_configuration_resources(
                    result.config
                )
            )

        has_errors = any(
            issue.level
            is IssueLevel.ERROR
            for issue in issues
        )

        if (
            result.config is None
            or has_errors
        ):
            return (
                None,
                tuple(issues),
            )

        return (
            result.config,
            tuple(issues),
        )

    def _log_issues(
        self,
        issues: tuple[
            ConfigIssue,
            ...,
        ],
    ) -> None:
        for issue in issues:
            log_method = (
                self._logger.error
                if issue.level
                is IssueLevel.ERROR
                else self._logger.warning
            )

            log_method(
                "%s: %s",
                issue.location,
                issue.message,
            )

    def _reload_configuration(
        self,
        *,
        initial: bool,
    ) -> bool:
        configuration, issues = (
            self._load_validated_configuration()
        )

        self._log_issues(
            issues
        )

        if configuration is None:
            if (
                self._configuration
                is None
                and self._tray
                is not None
            ):
                self._current_profile = None

                self._refresh_tray(
                    config_valid=False
                )

            if (
                self._configuration
                is None
            ):
                self._logger.error(
                    "No valid configuration "
                    "is available"
                )

            else:
                self._logger.warning(
                    "Invalid reload ignored; "
                    "keeping the previous "
                    "valid configuration"
                )

            return False

        current_profile_id = (
            self._current_profile.id
            if self._current_profile
            is not None
            else None
        )

        self._configuration = (
            configuration
        )

        if (
            current_profile_id
            is not None
        ):
            self._current_profile = next(
                (
                    profile
                    for profile
                    in configuration.profiles
                    if profile.id
                    == current_profile_id
                ),
                None,
            )

        if self._watcher is None:
            self._watcher = (
                WallpaperWatcher(
                    configuration=(
                        configuration
                    ),
                    mode=self._mode,
                    on_message=(
                        self._logger.info
                    ),
                    on_state_changed=(
                        self._on_profile_state_changed
                    ),
                )
            )

            self._watcher.start_listening(
                synchronize_initial=(
                    self._synchronize_initial
                    if initial
                    else True
                )
            )

        else:
            self._watcher.update_configuration(
                configuration,
                synchronize_current=True,
            )

        self._logger.info(
            "Configuration loaded: "
            "%d profile(s)",
            len(
                configuration.profiles
            ),
        )

        self._refresh_tray(
            config_valid=True
        )

        if (
            self._main_window
            is not None
        ):
            self._main_window.update_configuration(
                configuration,
                mode=self._mode,
                current_profile=(
                    self._current_profile
                ),
            )

        return True

    def do_shutdown(
        self,
    ) -> None:
        self._logger.info(
            "Cinnameleon "
            "application stopping"
        )

        if (
            self._reload_source_id
            is not None
        ):
            GLib.source_remove(
                self._reload_source_id
            )

            self._reload_source_id = None

        if self._watcher is not None:
            self._watcher.stop_listening()
            self._watcher = None

        if (
            self._config_monitor
            is not None
        ):
            self._config_monitor.cancel()
            self._config_monitor = None

        for source_id in (
            self._signal_source_ids
        ):
            GLib.source_remove(
                source_id
            )

        self._signal_source_ids.clear()

        if (
            self._main_window
            is not None
        ):
            self._main_window.destroy()
            self._main_window = None

        if self._tray is not None:
            self._tray.destroy()
            self._tray = None

        if self._held:
            self.release()
            self._held = False

        Gtk.Application.do_shutdown(
            self
        )