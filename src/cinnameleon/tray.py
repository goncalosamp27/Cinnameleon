"""Native Cinnamon tray icon using XAppStatusIcon."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("XApp", "1.0")

from gi.repository import Gtk, XApp

from cinnameleon.models import Mode, Profile


STATUS_ICON_NAME = "io.github.goncalosamp27.cinnameleon"
DEFAULT_ICON_NAME = "preferences-desktop-theme-symbolic"

ActionCallback = Callable[[], None]


class TrayIcon:
    """Cinnameleon status icon and tray menu."""

    def __init__(
        self,
        *,
        config_path: Path,
        on_reload: ActionCallback,
        on_open_config: ActionCallback,
        on_quit: ActionCallback,
    ) -> None:
        self._config_path = config_path
        self._on_reload = on_reload
        self._on_open_config = on_open_config
        self._on_quit = on_quit

        self._menu: Gtk.Menu | None = None
        self._status_icon = self._create_status_icon()

        self._status_icon.set_icon_name(DEFAULT_ICON_NAME)
        self._status_icon.set_tooltip_text("Cinnameleon")
        self._status_icon.set_visible(True)

        self.update_status(
            profile=None,
            mode=Mode.DARK,
            config_valid=False,
        )

    @staticmethod
    def _create_status_icon() -> XApp.StatusIcon:
        """Create a named XApp status icon."""

        if hasattr(XApp.StatusIcon, "new_with_name"):
            return XApp.StatusIcon.new_with_name(
                STATUS_ICON_NAME
            )

        icon = XApp.StatusIcon.new()
        icon.set_name(STATUS_ICON_NAME)

        return icon

    @staticmethod
    def _disabled_item(label: str) -> Gtk.MenuItem:
        """Create a non-interactive menu label."""

        item = Gtk.MenuItem(label=label)
        item.set_sensitive(False)

        return item

    @staticmethod
    def _separator() -> Gtk.SeparatorMenuItem:
        """Create a menu separator."""

        return Gtk.SeparatorMenuItem()

    def update_status(
        self,
        *,
        profile: Profile | None,
        mode: Mode,
        config_valid: bool,
    ) -> None:
        """Rebuild the tray menu using the current application state."""

        menu = Gtk.Menu()

        title_item = self._disabled_item("Cinnameleon")
        menu.append(title_item)

        menu.append(self._separator())

        current_title = self._disabled_item("Current profile")
        menu.append(current_title)

        if not config_valid:
            profile_label = "⚠ Invalid configuration"
        elif profile is None:
            profile_label = "No matching profile"
        else:
            profile_label = f"✓ {profile.name}"

        profile_item = self._disabled_item(profile_label)
        menu.append(profile_item)

        mode_item = self._disabled_item(
            f"Mode: {mode.value.capitalize()}"
        )
        menu.append(mode_item)

        menu.append(self._separator())

        reload_item = Gtk.MenuItem(
            label="Reload configuration"
        )
        reload_item.connect(
            "activate",
            self._handle_reload,
        )
        menu.append(reload_item)

        open_item = Gtk.MenuItem(
            label="Open config folder"
        )
        open_item.connect(
            "activate",
            self._handle_open_config,
        )
        menu.append(open_item)

        menu.append(self._separator())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect(
            "activate",
            self._handle_quit,
        )
        menu.append(quit_item)

        menu.show_all()

        self._status_icon.set_primary_menu(menu)
        self._status_icon.set_secondary_menu(menu)

        self._menu = menu

        if profile is not None:
            tooltip = (
                f"Cinnameleon — {profile.name} "
                f"({mode.value})"
            )
        elif config_valid:
            tooltip = "Cinnameleon — No matching profile"
        else:
            tooltip = "Cinnameleon — Invalid configuration"

        self._status_icon.set_tooltip_text(tooltip)

    def _handle_reload(
        self,
        _: Gtk.MenuItem,
    ) -> None:
        self._on_reload()

    def _handle_open_config(
        self,
        _: Gtk.MenuItem,
    ) -> None:
        self._on_open_config()

    def _handle_quit(
        self,
        _: Gtk.MenuItem,
    ) -> None:
        self._on_quit()

    def destroy(self) -> None:
        """Hide and release the tray icon."""

        self._status_icon.set_visible(False)
        self._menu = None