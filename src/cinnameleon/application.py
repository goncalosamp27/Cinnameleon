"""Resident single-instance Cinnameleon application."""

from __future__ import annotations

import logging
import signal
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gio, GLib, Gtk

from cinnameleon.config import load_configuration
from cinnameleon.logging_setup import configure_logging
from cinnameleon.models import (
    ConfigIssue,
    Configuration,
    IssueLevel,
    Mode,
    Profile,
)
from cinnameleon.validator import (
    validate_configuration_resources,
)
from cinnameleon.watcher import WallpaperWatcher

from cinnameleon.tray import TrayIcon


APPLICATION_ID = "io.github.goncalosamp27.cinnameleon"
RELOAD_DELAY_MS = 300


class CinnameleonApplication(Gtk.Application):
    """Single-instance resident application."""

    def __init__(
        self,
        *,
        config_path: Path,
        mode: Mode,
        synchronize_initial: bool = True,
        verbose: bool = False,
    ) -> None:
        super().__init__(
            application_id=APPLICATION_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

        self._config_path = config_path.resolve()
        self._mode = mode
        self._synchronize_initial = synchronize_initial

        self._logger = configure_logging(
            console=True,
            verbose=verbose,
        )

        self._configuration: Configuration | None = None
        self._watcher: WallpaperWatcher | None = None
        self._config_monitor: Gio.FileMonitor | None = None
        self._tray: TrayIcon | None = None

        self._reload_source_id: int | None = None
        self._signal_source_ids: list[int] = []
        self._held = False

    def do_startup(self) -> None:
        """Initialize long-running application services."""

        Gtk.Application.do_startup(self)

        self.hold()
        self._held = True

        self._install_unix_signal_handlers()

        self._tray = TrayIcon(
            config_path=self._config_path,
            on_reload=self._on_tray_reload,
            on_open_config=self._open_config_folder,
            on_quit=self.quit,
        )

        self._start_config_monitor()
        self._reload_configuration(initial=True)

        def _on_tray_reload(self) -> None:
            """Reload configuration from the tray menu."""

            self._logger.info(
                "Manual configuration reload requested"
            )
            self._reload_configuration(initial=False)


        def _open_config_folder(self) -> None:
            """Open the configuration directory."""

            uri = self._config_path.parent.as_uri()

            try:
                Gio.AppInfo.launch_default_for_uri(
                    uri,
                    None,
                )
            except GLib.Error as error:
                self._logger.error(
                    "Could not open configuration folder: %s",
                    error,
                )

        def _on_profile_state_changed(
            self,
            profile: Profile | None,
            mode: Mode,
        ) -> None:
            """Update the tray after profile synchronization."""

            if self._tray is None:
                return

            self._tray.update_status(
                profile=profile,
                mode=mode,
                config_valid=True,
            )

        self._reload_configuration(initial=True)

        self._logger.info(
            "Cinnameleon application started"
        )
        self._logger.info(
            "Configuration: %s",
            self._config_path,
        )
        self._logger.info("Mode: %s", self._mode.value)

    def do_activate(self) -> None:
        """Activate the existing or newly started instance."""

        self._logger.debug("Application activated")

    def do_shutdown(self) -> None:
        """Release monitors and signal handlers."""

        self._logger.info(
            "Cinnameleon application stopping"
        )

        if self._reload_source_id is not None:
            GLib.source_remove(self._reload_source_id)
            self._reload_source_id = None

        if self._watcher is not None:
            self._watcher.stop_listening()
            self._watcher = None

        if self._config_monitor is not None:
            self._config_monitor.cancel()
            self._config_monitor = None

        for source_id in self._signal_source_ids:
            GLib.source_remove(source_id)

        self._signal_source_ids.clear()

        if self._held:
            self.release()
            self._held = False

        if self._tray is not None:
            self._tray.destroy()
            self._tray = None

        Gtk.Application.do_shutdown(self)

    def _install_unix_signal_handlers(self) -> None:
        """Stop cleanly on Ctrl+C and session termination."""

        for signal_number in (
            signal.SIGINT,
            signal.SIGTERM,
        ):
            source_id = GLib.unix_signal_add(
                GLib.PRIORITY_DEFAULT,
                signal_number,
                self._on_unix_signal,
            )
            self._signal_source_ids.append(source_id)

    def _on_unix_signal(self) -> bool:
        """Quit after a Unix termination signal."""

        self._logger.info(
            "Termination signal received"
        )
        self.quit()

        return GLib.SOURCE_REMOVE
    
    def _on_tray_reload(self) -> None:
        """Reload configuration from the tray menu."""

        self._logger.info(
            "Manual configuration reload requested"
        )

        self._reload_configuration(initial=False)

    def _open_config_folder(self) -> None:
        """Open the configuration directory."""

        uri = self._config_path.parent.as_uri()

        try:
            Gio.AppInfo.launch_default_for_uri(
                uri,
                None,
            )
        except GLib.Error as error:
            self._logger.error(
                "Could not open configuration folder: %s",
                error,
            )

    def _on_profile_state_changed(
        self,
        profile: Profile | None,
        mode: Mode,
    ) -> None:
        """Update the tray after profile synchronization."""

        if self._tray is None:
            return

        self._tray.update_status(
            profile=profile,
            mode=mode,
            config_valid=True,
        )

    def _start_config_monitor(self) -> None:
        """Monitor the configuration directory for file changes."""

        self._config_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        config_directory = Gio.File.new_for_path(
            str(self._config_path.parent)
        )

        try:
            self._config_monitor = (
                config_directory.monitor_directory(
                    Gio.FileMonitorFlags.WATCH_MOVES,
                    None,
                )
            )
        except GLib.Error as error:
            self._logger.error(
                "Could not monitor configuration: %s",
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
        """Return whether a monitored file is config.yaml."""

        if file is None:
            return False

        file_path = file.get_path()

        if file_path is None:
            return False

        return Path(file_path).resolve() == self._config_path

    def _on_config_directory_changed(
        self,
        _: Gio.FileMonitor,
        file: Gio.File,
        other_file: Gio.File | None,
        event_type: Gio.FileMonitorEvent,
    ) -> None:
        """Debounce file monitor events for the config file."""

        if not (
            self._file_matches_config(file)
            or self._file_matches_config(other_file)
        ):
            return

        relevant_events = {
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.MOVED_IN,
            Gio.FileMonitorEvent.RENAMED,
        }

        if event_type not in relevant_events:
            return

        if self._reload_source_id is not None:
            GLib.source_remove(self._reload_source_id)

        self._reload_source_id = GLib.timeout_add(
            RELOAD_DELAY_MS,
            self._perform_scheduled_reload,
        )

    def _perform_scheduled_reload(self) -> bool:
        """Run one debounced configuration reload."""

        self._reload_source_id = None
        self._reload_configuration(initial=False)

        return GLib.SOURCE_REMOVE

    def _load_validated_configuration(
        self,
    ) -> tuple[
        Configuration | None,
        tuple[ConfigIssue, ...],
    ]:
        """Load YAML and validate installed resources."""

        result = load_configuration(self._config_path)
        issues = list(result.issues)

        if result.config is not None:
            issues.extend(
                validate_configuration_resources(
                    result.config
                )
            )

        has_errors = any(
            issue.level is IssueLevel.ERROR
            for issue in issues
        )

        if result.config is None or has_errors:
            return None, tuple(issues)

        return result.config, tuple(issues)

    def _log_issues(
        self,
        issues: tuple[ConfigIssue, ...],
    ) -> None:
        """Write configuration issues to the log."""

        for issue in issues:
            log_method = (
                self._logger.error
                if issue.level is IssueLevel.ERROR
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
        """Load new configuration while retaining the last valid one."""

        configuration, issues = (
            self._load_validated_configuration()
        )

        self._log_issues(issues)

        if configuration is None:
            if (
                self._configuration is None
                and self._tray is not None
            ):
                self._tray.update_status(
                    profile=None,
                    mode=self._mode,
                    config_valid=False,
                )
            if self._configuration is None:
                self._logger.error(
                    "No valid configuration is available"
                )
            else:
                self._logger.warning(
                    "Invalid reload ignored; keeping the "
                    "previous valid configuration"
                )

            return False

        self._configuration = configuration

        if self._watcher is None:
            self._watcher = WallpaperWatcher(
                configuration=configuration,
                mode=self._mode,
                on_message=self._logger.info,
                on_state_changed=(
                    self._on_profile_state_changed
                ),
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
            "Configuration loaded: %d profile(s)",
            len(configuration.profiles),
        )

        return True