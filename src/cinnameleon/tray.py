"""Native interactive Cinnamon tray icon using XAppStatusIcon."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("XApp", "1.0")

from gi.repository import Gtk, XApp

from cinnameleon.models import Mode, Profile


STATUS_ICON_NAME = (
    "io.github.goncalosamp27.cinnameleon"
)

TRAY_ICON_NAME = (
    "io.github.goncalosamp27."
    "cinnameleon-tray-symbolic"
)

FALLBACK_ICON_NAME = (
    "preferences-desktop-theme-symbolic"
)

ActionCallback = Callable[[], None]
ProfileSelectedCallback = Callable[[str], None]
ModeChangedCallback = Callable[[Mode], None]


class TrayIcon:
    """Cinnameleon status icon and menu."""

    def __init__(
        self,
        *,
        config_path: Path,
        on_open_window: ActionCallback,
        on_profile_selected: ProfileSelectedCallback,
        on_mode_changed: ModeChangedCallback,
        on_reload: ActionCallback,
        on_open_config: ActionCallback,
        on_quit: ActionCallback,
    ) -> None:
        self._config_path = config_path

        self._on_open_window = (
            on_open_window
        )

        self._on_profile_selected = (
            on_profile_selected
        )

        self._on_mode_changed = (
            on_mode_changed
        )

        self._on_reload = on_reload

        self._on_open_config = (
            on_open_config
        )

        self._on_quit = on_quit

        self._menu: Gtk.Menu | None = None

        self._status_icon = (
            self._create_status_icon()
        )

        self._status_icon.set_icon_name(
            self._resolve_icon_name()
        )

        self._status_icon.set_tooltip_text(
            "Cinnameleon"
        )

        self._status_icon.set_visible(
            True
        )

        self.update_status(
            profiles=(),
            current_profile=None,
            mode=Mode.DARK,
            config_valid=False,
        )

    @staticmethod
    def _resolve_icon_name() -> str:
        icon_theme = (
            Gtk.IconTheme.get_default()
        )

        if (
            icon_theme is not None
            and icon_theme.has_icon(
                TRAY_ICON_NAME
            )
        ):
            return TRAY_ICON_NAME

        return FALLBACK_ICON_NAME

    @staticmethod
    def _create_status_icon(
    ) -> XApp.StatusIcon:
        if hasattr(
            XApp.StatusIcon,
            "new_with_name",
        ):
            return (
                XApp.StatusIcon
                .new_with_name(
                    STATUS_ICON_NAME
                )
            )

        icon = XApp.StatusIcon.new()

        icon.set_name(
            STATUS_ICON_NAME
        )

        return icon

    @staticmethod
    def _disabled_item(
        label: str,
    ) -> Gtk.MenuItem:
        item = Gtk.MenuItem(
            label=label
        )

        item.set_sensitive(False)

        return item

    @staticmethod
    def _separator(
    ) -> Gtk.SeparatorMenuItem:
        return Gtk.SeparatorMenuItem()

    def _build_profile_submenu(
        self,
        profiles: tuple[Profile, ...],
        current_profile: Profile | None,
        *,
        sensitive: bool,
    ) -> Gtk.MenuItem:
        parent_item = Gtk.MenuItem(
            label="Theme profile"
        )

        submenu = Gtk.Menu()

        first_radio_item: (
            Gtk.RadioMenuItem | None
        ) = None

        for profile in profiles:
            if first_radio_item is None:
                radio_item = (
                    Gtk.RadioMenuItem
                    .new_with_label(
                        None,
                        profile.name,
                    )
                )

                first_radio_item = (
                    radio_item
                )

            else:
                radio_item = (
                    Gtk.RadioMenuItem
                    .new_with_label_from_widget(
                        first_radio_item,
                        profile.name,
                    )
                )

            is_current = (
                current_profile is not None
                and current_profile.id
                == profile.id
            )

            radio_item.set_active(
                is_current
            )

            radio_item.connect(
                "toggled",
                self._handle_profile_toggled,
                profile.id,
            )

            submenu.append(
                radio_item
            )

        if not profiles:
            submenu.append(
                self._disabled_item(
                    "No valid profiles available"
                )
            )

        parent_item.set_submenu(
            submenu
        )

        parent_item.set_sensitive(
            sensitive
            and bool(profiles)
        )

        return parent_item

    def update_status(
        self,
        *,
        profiles: tuple[Profile, ...],
        current_profile: Profile | None,
        mode: Mode,
        config_valid: bool,
    ) -> None:
        menu = Gtk.Menu()

        open_window = Gtk.MenuItem(
            label="Open Cinnameleon"
        )

        open_window.connect(
            "activate",
            self._handle_open_window,
        )

        menu.append(
            open_window
        )

        menu.append(
            self._separator()
        )

        menu.append(
            self._disabled_item(
                "Current profile"
            )
        )

        if not config_valid:
            current_label = (
                "⚠ Invalid configuration"
            )

        elif current_profile is None:
            current_label = (
                "No matching profile"
            )

        else:
            current_label = (
                f"✓ {current_profile.name}"
            )

        menu.append(
            self._disabled_item(
                current_label
            )
        )

        menu.append(
            self._separator()
        )

        menu.append(
            self._build_profile_submenu(
                profiles,
                current_profile,
                sensitive=config_valid,
            )
        )

        dark_mode = Gtk.CheckMenuItem(
            label="Dark mode"
        )

        dark_mode.set_active(
            mode is Mode.DARK
        )

        dark_mode.set_sensitive(
            config_valid
        )

        dark_mode.connect(
            "toggled",
            self._handle_mode_toggled,
        )

        menu.append(
            dark_mode
        )

        menu.append(
            self._separator()
        )

        reload_item = Gtk.MenuItem(
            label="Reload configuration"
        )

        reload_item.connect(
            "activate",
            self._handle_reload,
        )

        menu.append(
            reload_item
        )

        open_config = Gtk.MenuItem(
            label="Open config folder"
        )

        open_config.connect(
            "activate",
            self._handle_open_config,
        )

        menu.append(
            open_config
        )

        menu.append(
            self._separator()
        )

        quit_item = Gtk.MenuItem(
            label="Quit"
        )

        quit_item.connect(
            "activate",
            self._handle_quit,
        )

        menu.append(
            quit_item
        )

        menu.show_all()

        self._status_icon.set_primary_menu(
            menu
        )

        self._status_icon.set_secondary_menu(
            menu
        )

        self._menu = menu

        if current_profile is not None:
            tooltip = (
                "Cinnameleon: "
                f"{current_profile.name} "
                f"({mode.value})"
            )

        elif config_valid:
            tooltip = (
                "Cinnameleon: "
                "No matching profile"
            )

        else:
            tooltip = (
                "Cinnameleon: "
                "Invalid configuration"
            )

        self._status_icon.set_tooltip_text(
            tooltip
        )

    def _handle_open_window(
        self,
        _: Gtk.MenuItem,
    ) -> None:
        self._on_open_window()

    def _handle_profile_toggled(
        self,
        item: Gtk.RadioMenuItem,
        profile_id: str,
    ) -> None:
        if not item.get_active():
            return

        self._on_profile_selected(
            profile_id
        )

    def _handle_mode_toggled(
        self,
        item: Gtk.CheckMenuItem,
    ) -> None:
        mode = (
            Mode.DARK
            if item.get_active()
            else Mode.LIGHT
        )

        self._on_mode_changed(
            mode
        )

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

    def destroy(
        self,
    ) -> None:
        self._status_icon.set_visible(
            False
        )

        self._menu = None