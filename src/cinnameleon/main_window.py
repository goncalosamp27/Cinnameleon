"""Main graphical window for Cinnameleon."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import GdkPixbuf, Gtk, Pango

from cinnameleon.models import (
    Configuration,
    EffectiveAppearance,
    EffectiveProfile,
    FontSettings,
    Mode,
    Profile,
)
from cinnameleon.resolver import resolve_profile
from cinnameleon.resources import ResourceCatalog

from cinnameleon.resource_picker import (
    CursorThemePickerDialog,
    FontPickerDialog,
    GtkThemePickerDialog,
    IconThemePickerDialog,
)

ApplyCallback = Callable[
    [EffectiveProfile],
    bool,
]

SaveCallback = Callable[
    [EffectiveProfile],
    bool,
]

NewProfileCallback = Callable[
    [str, Path],
    str | None,
]

DuplicateProfileCallback = Callable[
    [str],
    str | None,
]

DeleteProfileCallback = Callable[
    [str],
    bool,
]

WallpaperCallback = Callable[
    [str, Path],
    bool,
]


KEEP = "__keep_current__"


class MainWindow(
    Gtk.ApplicationWindow
):
    """Graphical Cinnameleon profile editor."""

    def __init__(
        self,
        *,
        application: Gtk.Application,
        configuration: Configuration,
        mode: Mode,
        current_profile: Profile | None,
        on_apply: ApplyCallback,
        on_save: SaveCallback,
        on_new_profile: NewProfileCallback,
        on_duplicate_profile: DuplicateProfileCallback,
        on_delete_profile: DeleteProfileCallback,
        on_change_wallpaper: WallpaperCallback,
    ) -> None:
        super().__init__(
            application=application
        )

        self._configuration = (
            configuration
        )

        self._mode = mode

        self._current_profile = (
            current_profile
        )

        self._on_apply = on_apply
        self._on_save = on_save

        self._on_new_profile = (
            on_new_profile
        )

        self._on_duplicate_profile = (
            on_duplicate_profile
        )

        self._on_delete_profile = (
            on_delete_profile
        )

        self._on_change_wallpaper = (
            on_change_wallpaper
        )

        self._selected_profile_id: (
            str | None
        ) = None

        self._rows: dict[
            str,
            Gtk.ListBoxRow,
        ] = {}

        self._updating_mode = False

        self._catalog = (
            ResourceCatalog.discover()
        )

        self.set_title(
            "Cinnameleon"
        )

        self.set_default_size(
            1100,
            720,
        )

        self.set_size_request(
            900,
            600,
        )

        self.connect(
            "delete-event",
            self._hide_on_close,
        )

        self._build_ui()

        self.update_configuration(
            configuration,
            mode=mode,
            current_profile=current_profile,
        )

    # ---------------------------------------------------------
    # Build UI
    # ---------------------------------------------------------

    def _build_ui(
        self,
    ) -> None:
        header = Gtk.HeaderBar(
            title="Cinnameleon"
        )

        header.set_subtitle(
            "Appearance profiles for your workspace"
        )

        header.set_show_close_button(
            True
        )

        self.set_titlebar(
            header
        )

        self._apply_button = Gtk.Button(
            label="Apply"
        )

        self._apply_button.get_style_context().add_class(
            "suggested-action"
        )

        self._apply_button.connect(
            "clicked",
            self._apply,
        )

        header.pack_end(
            self._apply_button
        )

        self._save_button = Gtk.Button(
            label="Save"
        )

        self._save_button.connect(
            "clicked",
            self._save,
        )

        header.pack_end(
            self._save_button
        )

        refresh = (
            Gtk.Button.new_from_icon_name(
                "view-refresh-symbolic",
                Gtk.IconSize.BUTTON,
            )
        )

        refresh.set_tooltip_text(
            "Refresh installed themes and fonts"
        )

        refresh.connect(
            "clicked",
            self._refresh_resources,
        )

        header.pack_end(
            refresh
        )

        root = Gtk.Paned.new(
            Gtk.Orientation.HORIZONTAL
        )

        root.set_position(
            240
        )

        self.add(
            root
        )

        root.pack1(
            self._build_sidebar(),
            resize=False,
            shrink=False,
        )

        root.pack2(
            self._build_editor(),
            resize=True,
            shrink=False,
        )

    def _build_sidebar(
        self,
    ) -> Gtk.Widget:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )

        box.set_size_request(
            240,
            -1,
        )

        box.set_border_width(
            12
        )

        title = Gtk.Label(
            label="PROFILES"
        )

        title.set_xalign(
            0
        )

        box.pack_start(
            title,
            False,
            False,
            4,
        )

        self._profile_list = (
            Gtk.ListBox()
        )

        self._profile_list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )

        self._profile_list.connect(
            "row-selected",
            self._profile_selected,
        )

        scroll = Gtk.ScrolledWindow()

        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )

        scroll.add(
            self._profile_list
        )

        box.pack_start(
            scroll,
            True,
            True,
            0,
        )

        actions = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
        )

        self._new_button = (
            Gtk.Button.new_from_icon_name(
                "list-add-symbolic",
                Gtk.IconSize.BUTTON,
            )
        )

        self._new_button.set_tooltip_text(
            "New profile"
        )

        self._new_button.connect(
            "clicked",
            self._new_profile,
        )

        actions.pack_start(
            self._new_button,
            True,
            True,
            0,
        )

        self._duplicate_button = (
            Gtk.Button.new_from_icon_name(
                "edit-copy-symbolic",
                Gtk.IconSize.BUTTON,
            )
        )

        self._duplicate_button.set_tooltip_text(
            "Duplicate profile"
        )

        self._duplicate_button.connect(
            "clicked",
            self._duplicate_profile,
        )

        actions.pack_start(
            self._duplicate_button,
            True,
            True,
            0,
        )

        self._delete_button = (
            Gtk.Button.new_from_icon_name(
                "edit-delete-symbolic",
                Gtk.IconSize.BUTTON,
            )
        )

        self._delete_button.set_tooltip_text(
            "Delete profile"
        )

        self._delete_button.connect(
            "clicked",
            self._delete_profile,
        )

        actions.pack_start(
            self._delete_button,
            True,
            True,
            0,
        )

        box.pack_end(
            actions,
            False,
            False,
            0,
        )

        return box

    def _build_editor(
        self,
    ) -> Gtk.Widget:
        scroll = Gtk.ScrolledWindow()

        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )

        box.set_border_width(
            24
        )

        scroll.add(
            box
        )

        top = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )

        box.pack_start(
            top,
            False,
            False,
            0,
        )

        names = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
        )

        top.pack_start(
            names,
            True,
            True,
            0,
        )

        self._profile_name = Gtk.Entry()

        self._profile_name.set_placeholder_text(
            "Profile name"
        )

        names.pack_start(
            self._profile_name,
            False,
            False,
            0,
        )

        self._profile_id = Gtk.Label()

        self._profile_id.set_xalign(
            0
        )

        names.pack_start(
            self._profile_id,
            False,
            False,
            0,
        )

        mode_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        top.pack_end(
            mode_box,
            False,
            False,
            0,
        )

        mode_box.pack_start(
            Gtk.Label(
                label="Light"
            ),
            False,
            False,
            0,
        )

        self._mode_switch = (
            Gtk.Switch()
        )

        self._mode_switch.connect(
            "notify::active",
            self._mode_changed,
        )

        mode_box.pack_start(
            self._mode_switch,
            False,
            False,
            0,
        )

        mode_box.pack_start(
            Gtk.Label(
                label="Dark"
            ),
            False,
            False,
            0,
        )

        self._wallpaper = Gtk.Image()

        self._wallpaper.set_size_request(
            -1,
            260,
        )

        box.pack_start(
            self._wallpaper,
            False,
            False,
            0,
        )

        wallpaper_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        self._wallpaper_path = (
            Gtk.Label()
        )

        self._wallpaper_path.set_xalign(
            0
        )

        self._wallpaper_path.set_ellipsize(
            Pango.EllipsizeMode.MIDDLE
        )

        wallpaper_row.pack_start(
            self._wallpaper_path,
            True,
            True,
            0,
        )

        wallpaper_button = Gtk.Button(
            label="Change wallpaper…"
        )

        wallpaper_button.connect(
            "clicked",
            self._change_wallpaper,
        )

        wallpaper_row.pack_end(
            wallpaper_button,
            False,
            False,
            0,
        )

        box.pack_start(
            wallpaper_row,
            False,
            False,
            0,
        )

        desktop = self._section(
            "Desktop"
        )

        box.pack_start(
            desktop,
            False,
            False,
            0,
        )

        desktop_grid = Gtk.Grid(
            column_spacing=18,
            row_spacing=10,
        )

        desktop.pack_start(
            desktop_grid,
            False,
            False,
            0,
        )

        self._gtk = (
            Gtk.ComboBoxText()
        )

        gtk_picker = Gtk.Button(
            label="Browse…"
        )

        gtk_picker.set_tooltip_text(
            "Browse GTK themes with preview"
        )

        gtk_picker.connect(
            "clicked",
            self._browse_gtk_theme,
        )

        self._cinnamon = (
            Gtk.ComboBoxText()
        )

        self._borders = (
            Gtk.ComboBoxText()
        )

        self._icons = (
            Gtk.ComboBoxText()
        )

        icon_picker = Gtk.Button(
            label="Browse…"
        )

        icon_picker.set_tooltip_text(
            "Browse icon themes with preview"
        )

        icon_picker.connect(
            "clicked",
            self._browse_icon_theme,
        )

        self._cursor = (
            Gtk.ComboBoxText()
        )

        cursor_picker = Gtk.Button(
            label="Browse…"
        )

        cursor_picker.set_tooltip_text(
            "Browse cursor themes with preview"
        )

        cursor_picker.connect(
            "clicked",
            self._browse_cursor_theme,
        )

        self._row(
            desktop_grid,
            0,
            "GTK theme",
            self._gtk,
            gtk_picker,
        )

        self._row(
            desktop_grid,
            1,
            "Cinnamon theme",
            self._cinnamon,
        )

        self._row(
            desktop_grid,
            2,
            "Window borders",
            self._borders,
        )

        self._row(
            desktop_grid,
            3,
            "Icon theme",
            self._icons,
            icon_picker,
        )

        self._row(
            desktop_grid,
            4,
            "Cursor theme",
            self._cursor,
            cursor_picker,
        )

        self._cinnamon.set_sensitive(
            False
        )

        self._cinnamon.set_tooltip_text(
            "Disabled for session safety for now"
        )

        typography = self._section(
            "Typography"
        )

        box.pack_start(
            typography,
            False,
            False,
            0,
        )

        font_grid = Gtk.Grid(
            column_spacing=18,
            row_spacing=10,
        )

        typography.pack_start(
            font_grid,
            False,
            False,
            0,
        )

        self._interface_font = (
            Gtk.ComboBoxText()
        )

        self._document_font = (
            Gtk.ComboBoxText()
        )

        self._mono_font = (
            Gtk.ComboBoxText()
        )

        self._title_font = (
            Gtk.ComboBoxText()
        )

        interface_font_picker = Gtk.Button(
            label="Browse…"
        )

        interface_font_picker.connect(
            "clicked",
            self._browse_font,
            self._interface_font,
        )

        document_font_picker = Gtk.Button(
            label="Browse…"
        )

        document_font_picker.connect(
            "clicked",
            self._browse_font,
            self._document_font,
        )

        mono_font_picker = Gtk.Button(
            label="Browse…"
        )

        mono_font_picker.connect(
            "clicked",
            self._browse_font,
            self._mono_font,
        )

        title_font_picker = Gtk.Button(
            label="Browse…"
        )

        title_font_picker.connect(
            "clicked",
            self._browse_font,
            self._title_font,
        )

        self._row(
            font_grid,
            0,
            "Interface font",
            self._interface_font,
            interface_font_picker,
        )

        self._row(
            font_grid,
            1,
            "Document font",
            self._document_font,
            document_font_picker,
        )

        self._row(
            font_grid,
            2,
            "Monospace font",
            self._mono_font,
            mono_font_picker,
        )

        self._row(
            font_grid,
            3,
            "Window title font",
            self._title_font,
            title_font_picker,
        )

        self._font_preview = Gtk.Label(
            label=(
                "The quick brown fox jumps over "
                "the lazy dog. 0123456789"
            )
        )

        self._font_preview.set_xalign(
            0
        )

        self._font_preview.set_margin_top(
            10
        )

        typography.pack_start(
            self._font_preview,
            False,
            False,
            0,
        )

        self._interface_font.connect(
            "changed",
            self._update_font_preview,
        )

        self._resource_summary = (
            Gtk.Label()
        )

        self._resource_summary.set_xalign(
            0
        )

        box.pack_start(
            self._resource_summary,
            False,
            False,
            0,
        )

        self._status = Gtk.Label()

        self._status.set_xalign(
            0
        )

        self._status.set_line_wrap(
            True
        )

        box.pack_start(
            self._status,
            False,
            False,
            0,
        )

        return scroll

    @staticmethod
    def _section(
        title: str,
    ) -> Gtk.Box:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )

        label = Gtk.Label(
            label=title
        )

        label.set_xalign(
            0
        )

        box.pack_start(
            label,
            False,
            False,
            0,
        )

        return box

    @staticmethod
    def _row(
        grid: Gtk.Grid,
        row: int,
        text: str,
        combo: Gtk.ComboBoxText,
        action: Gtk.Widget | None = None,
    ) -> None:
        label = Gtk.Label(
            label=text
        )

        label.set_xalign(
            0
        )

        grid.attach(
            label,
            0,
            row,
            1,
            1,
        )

        combo.set_hexpand(
            True
        )

        grid.attach(
            combo,
            1,
            row,
            1,
            1,
        )

        if action is not None:
            grid.attach(
                action,
                2,
                row,
                1,
                1,
            )

    # ---------------------------------------------------------
    # Configuration / selection
    # ---------------------------------------------------------

    def update_configuration(
        self,
        configuration: Configuration,
        *,
        mode: Mode,
        current_profile: Profile | None,
    ) -> None:
        previous = (
            self._selected_profile_id
        )

        self._configuration = (
            configuration
        )

        self._mode = mode

        self._current_profile = (
            current_profile
        )

        for child in (
            self._profile_list
            .get_children()
        ):
            self._profile_list.remove(
                child
            )

        self._rows.clear()

        for profile in (
            configuration.profiles
        ):
            row = Gtk.ListBoxRow()

            row.profile_id = (
                profile.id
            )

            line = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=8,
            )

            name = Gtk.Label(
                label=profile.name
            )

            name.set_xalign(
                0
            )

            name.set_hexpand(
                True
            )

            line.pack_start(
                name,
                True,
                True,
                0,
            )

            if (
                current_profile is not None
                and current_profile.id
                == profile.id
            ):
                line.pack_end(
                    Gtk.Label(
                        label="●"
                    ),
                    False,
                    False,
                    0,
                )

            row.add(
                line
            )

            self._profile_list.add(
                row
            )

            self._rows[
                profile.id
            ] = row

        self._profile_list.show_all()

        self._updating_mode = True

        self._mode_switch.set_active(
            mode is Mode.DARK
        )

        self._updating_mode = False

        selected = (
            previous
            if previous
            in self._rows
            else None
        )

        if (
            selected is None
            and current_profile
            is not None
        ):
            selected = (
                current_profile.id
            )

        if (
            selected is None
            and configuration.profiles
        ):
            selected = (
                configuration
                .profiles[0]
                .id
            )

        if selected is not None:
            self._select_profile_by_id(
                selected
            )

        else:
            self._selected_profile_id = (
                None
            )

            self._apply_button.set_sensitive(
                False
            )

            self._save_button.set_sensitive(
                False
            )

        self._update_action_sensitivity()
        self._update_resource_summary()

    def set_active_state(
        self,
        profile: Profile | None,
        mode: Mode,
    ) -> None:
        new_id = (
            profile.id
            if profile is not None
            else None
        )

        if (
            new_id
            == (
                self._current_profile.id
                if self._current_profile
                is not None
                else None
            )
            and mode is self._mode
        ):
            return

        self.update_configuration(
            self._configuration,
            mode=mode,
            current_profile=profile,
        )

    def _select_profile_by_id(
        self,
        profile_id: str,
    ) -> None:
        row = self._rows.get(
            profile_id
        )

        if row is None:
            return

        self._profile_list.select_row(
            row
        )

        row.grab_focus()

    def _profile_selected(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if row is None:
            return

        self._selected_profile_id = getattr(
            row,
            "profile_id",
            None,
        )

        self._update_action_sensitivity()
        self._load_selected_profile()

    def _selected_profile(
        self,
    ) -> Profile | None:
        return next(
            (
                profile
                for profile
                in self._configuration.profiles
                if profile.id
                == self._selected_profile_id
            ),
            None,
        )

    def _update_action_sensitivity(
        self,
    ) -> None:
        has_selection = (
            self._selected_profile()
            is not None
        )

        self._duplicate_button.set_sensitive(
            has_selection
        )

        self._delete_button.set_sensitive(
            has_selection
            and len(
                self._configuration.profiles
            ) > 1
        )

    # ---------------------------------------------------------
    # Load profile into editor
    # ---------------------------------------------------------

    def _load_selected_profile(
        self,
    ) -> None:
        profile = (
            self._selected_profile()
        )

        if profile is None:
            self._apply_button.set_sensitive(
                False
            )

            self._save_button.set_sensitive(
                False
            )

            return

        effective = resolve_profile(
            self._configuration,
            profile.id,
            self._mode,
        )

        appearance = (
            effective.appearance
        )

        self._apply_button.set_sensitive(
            True
        )

        self._save_button.set_sensitive(
            True
        )

        self._profile_name.set_text(
            profile.name
        )

        self._profile_id.set_text(
            f"Profile ID: {profile.id}"
        )

        self._wallpaper_path.set_text(
            str(
                profile.wallpaper
            )
        )

        self._load_wallpaper(
            profile
        )

        self._populate(
            self._gtk,
            self._catalog.gtk_themes,
            appearance.gtk_theme,
        )

        self._populate(
            self._cinnamon,
            self._catalog.cinnamon_themes,
            appearance.cinnamon_theme,
        )

        self._populate(
            self._borders,
            self._catalog.window_border_themes,
            appearance.window_borders,
        )

        self._populate(
            self._icons,
            self._catalog.icon_themes,
            appearance.icon_theme,
        )

        self._populate(
            self._cursor,
            self._catalog.cursor_themes,
            appearance.cursor_theme,
        )

        self._populate_font(
            self._interface_font,
            appearance.fonts.interface,
        )

        self._populate_font(
            self._document_font,
            appearance.fonts.document,
        )

        self._populate_font(
            self._mono_font,
            appearance.fonts.monospace,
        )

        self._populate_font(
            self._title_font,
            appearance.fonts.window_title,
        )

        self._update_font_preview()

        self._status.set_text(
            "Ready."
        )

    # ---------------------------------------------------------
    # Resource selectors
    # ---------------------------------------------------------

    @staticmethod
    def _populate(
        combo: Gtk.ComboBoxText,
        values: Sequence[str],
        current: str | None,
    ) -> None:
        combo.remove_all()

        combo.append(
            KEEP,
            "Keep current system value",
        )

        options = list(
            values
        )

        if (
            current is not None
            and current not in options
        ):
            options.append(
                current
            )

            options.sort(
                key=str.casefold
            )

        for value in options:
            combo.append(
                value,
                value,
            )

        combo.set_active_id(
            current
            if current is not None
            else KEEP
        )

    def _populate_font(
        self,
        combo: Gtk.ComboBoxText,
        description: str | None,
    ) -> None:
        family = self._font_family(
            description
        )

        self._populate(
            combo,
            self._catalog.font_families,
            family,
        )

        combo._cinnameleon_font_description = (
            description
        )

    @staticmethod
    def _font_family(
        description: str | None,
    ) -> str | None:
        if description is None:
            return None

        family = (
            Pango.FontDescription
            .from_string(
                description
            )
            .get_family()
        )

        if not family:
            return None

        return family.strip()

    @staticmethod
    def _value(
        combo: Gtk.ComboBoxText,
    ) -> str | None:
        value = (
            combo.get_active_id()
        )

        if value in (
            None,
            KEEP,
        ):
            return None

        return value

    def _font_value(
        self,
        combo: Gtk.ComboBoxText,
    ) -> str | None:
        family = self._value(
            combo
        )

        if family is None:
            return None

        base = getattr(
            combo,
            "_cinnameleon_font_description",
            None,
        )

        description = (
            Pango.FontDescription
            .from_string(
                base or "Sans 10"
            )
        )

        description.set_family(
            family
        )

        return description.to_string()

    def _browse_gtk_theme(
        self,
        _: Gtk.Button,
    ) -> None:
        current = (
            self._gtk.get_active_id()
        )

        if current == KEEP:
            current = None

        dialog = GtkThemePickerDialog(
            parent=self,
            themes=self._catalog.gtk_themes,
            current=current,
        )

        selected = dialog.choose()

        if selected is None:
            return

        self._gtk.set_active_id(
            selected
        )

        self._status.set_text(
            f"GTK theme selected: {selected}"
        )

    def _browse_icon_theme(
        self,
        _: Gtk.Button,
    ) -> None:
        current = (
            self._icons.get_active_id()
        )

        if current == KEEP:
            current = None

        dialog = IconThemePickerDialog(
            parent=self,
            themes=self._catalog.icon_themes,
            current=current,
        )

        selected = dialog.choose()

        if selected is None:
            return

        self._icons.set_active_id(
            selected
        )

        self._status.set_text(
            f"Icon theme selected: {selected}"
        )

    def _browse_cursor_theme(
        self,
        _: Gtk.Button,
    ) -> None:
        current = (
            self._cursor.get_active_id()
        )

        if current == KEEP:
            current = None

        dialog = CursorThemePickerDialog(
            parent=self,
            themes=self._catalog.cursor_themes,
            current=current,
        )

        selected = dialog.choose()

        if selected is None:
            return

        self._cursor.set_active_id(
            selected
        )

        self._status.set_text(
            f"Cursor theme selected: {selected}"
        )

    def _browse_font(
        self,
        _: Gtk.Button,
        combo: Gtk.ComboBoxText,
    ) -> None:
        current = (
            combo.get_active_id()
        )

        if current == KEEP:
            current = None

        dialog = FontPickerDialog(
            parent=self,
            fonts=self._catalog.font_families,
            current=current,
        )

        selected = dialog.choose()

        if selected is None:
            return

        combo.set_active_id(
            selected
        )

        if combo is self._interface_font:
            self._update_font_preview()

        self._status.set_text(
            f"Font selected: {selected}"
        )

    # ---------------------------------------------------------
    # Wallpaper
    # ---------------------------------------------------------

    def _load_wallpaper(
        self,
        profile: Profile,
    ) -> None:
        try:
            pixbuf = (
                GdkPixbuf.Pixbuf
                .new_from_file_at_scale(
                    str(
                        profile.wallpaper
                    ),
                    900,
                    260,
                    True,
                )
            )

            self._wallpaper.set_from_pixbuf(
                pixbuf
            )

        except Exception:
            self._wallpaper.set_from_icon_name(
                "image-missing",
                Gtk.IconSize.DIALOG,
            )

    def _choose_wallpaper(
        self,
        title: str,
    ) -> Path | None:
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=self,
            action=(
                Gtk.FileChooserAction.OPEN
            ),
        )

        dialog.add_buttons(
            "Cancel",
            Gtk.ResponseType.CANCEL,
            "Choose",
            Gtk.ResponseType.OK,
        )

        image_filter = Gtk.FileFilter()

        image_filter.set_name(
            "Images"
        )

        image_filter.add_mime_type(
            "image/*"
        )

        dialog.add_filter(
            image_filter
        )

        all_filter = Gtk.FileFilter()

        all_filter.set_name(
            "All files"
        )

        all_filter.add_pattern(
            "*"
        )

        dialog.add_filter(
            all_filter
        )

        pictures = (
            Path.home()
            / "Pictures"
        )

        if pictures.is_dir():
            dialog.set_current_folder(
                str(pictures)
            )

        response = dialog.run()

        filename = (
            dialog.get_filename()
            if response
            == Gtk.ResponseType.OK
            else None
        )

        dialog.destroy()

        if filename is None:
            return None

        return Path(
            filename
        )

    def _change_wallpaper(
        self,
        _: Gtk.Button,
    ) -> None:
        profile = (
            self._selected_profile()
        )

        if profile is None:
            return

        wallpaper = self._choose_wallpaper(
            f"Choose wallpaper for {profile.name}"
        )

        if wallpaper is None:
            return

        self._status.set_text(
            "Importing wallpaper..."
        )

        success = (
            self._on_change_wallpaper(
                profile.id,
                wallpaper,
            )
        )

        if success:
            self._status.set_text(
                "Wallpaper updated."
            )

        else:
            self._status.set_text(
                "Could not update wallpaper."
            )

    # ---------------------------------------------------------
    # New / duplicate / delete
    # ---------------------------------------------------------

    def _new_profile(
        self,
        _: Gtk.Button,
    ) -> None:
        dialog = Gtk.Dialog(
            title="New Profile",
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Choose wallpaper…",
            Gtk.ResponseType.OK,
        )

        content = (
            dialog.get_content_area()
        )

        content.set_spacing(
            10
        )

        content.set_border_width(
            16
        )

        label = Gtk.Label(
            label="Profile name"
        )

        label.set_xalign(
            0
        )

        entry = Gtk.Entry()

        entry.set_placeholder_text(
            "e.g. Gengar"
        )

        entry.set_activates_default(
            True
        )

        content.pack_start(
            label,
            False,
            False,
            0,
        )

        content.pack_start(
            entry,
            False,
            False,
            0,
        )

        dialog.set_default_response(
            Gtk.ResponseType.OK
        )

        dialog.show_all()

        response = dialog.run()

        name = (
            entry.get_text()
            .strip()
        )

        dialog.destroy()

        if (
            response
            != Gtk.ResponseType.OK
        ):
            return

        if not name:
            self._status.set_text(
                "Profile name cannot be empty."
            )

            return

        wallpaper = self._choose_wallpaper(
            f"Choose wallpaper for {name}"
        )

        if wallpaper is None:
            return

        new_id = (
            self._on_new_profile(
                name,
                wallpaper,
            )
        )

        if new_id is None:
            self._status.set_text(
                "Could not create profile."
            )

            return

        self._select_profile_by_id(
            new_id
        )

        self._status.set_text(
            f"Created profile '{name}'."
        )

    def _duplicate_profile(
        self,
        _: Gtk.Button,
    ) -> None:
        profile = (
            self._selected_profile()
        )

        if profile is None:
            return

        new_id = (
            self._on_duplicate_profile(
                profile.id
            )
        )

        if new_id is None:
            self._status.set_text(
                "Could not duplicate profile."
            )

            return

        self._select_profile_by_id(
            new_id
        )

        self._status.set_text(
            "Profile duplicated."
        )

    def _delete_profile(
        self,
        _: Gtk.Button,
    ) -> None:
        profile = (
            self._selected_profile()
        )

        if profile is None:
            return

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=(
                Gtk.MessageType.WARNING
            ),
            buttons=Gtk.ButtonsType.NONE,
            text=(
                f"Delete '{profile.name}'?"
            ),
        )

        dialog.format_secondary_text(
            "The profile will be removed from "
            "config.yaml. Its wallpaper file "
            "will be kept."
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Delete",
            Gtk.ResponseType.OK,
        )

        response = dialog.run()

        dialog.destroy()

        if (
            response
            != Gtk.ResponseType.OK
        ):
            return

        success = (
            self._on_delete_profile(
                profile.id
            )
        )

        if success:
            self._status.set_text(
                "Profile deleted."
            )

        else:
            self._status.set_text(
                "Could not delete profile."
            )

    # ---------------------------------------------------------
    # Mode
    # ---------------------------------------------------------

    def _mode_changed(
        self,
        switch: Gtk.Switch,
        _: object,
    ) -> None:
        if self._updating_mode:
            return

        self._mode = (
            Mode.DARK
            if switch.get_active()
            else Mode.LIGHT
        )

        self._load_selected_profile()

    # ---------------------------------------------------------
    # Build effective preview
    # ---------------------------------------------------------

    def _build_preview(
        self,
    ) -> EffectiveProfile | None:
        profile = (
            self._selected_profile()
        )

        if profile is None:
            return None

        resolved = resolve_profile(
            self._configuration,
            profile.id,
            self._mode,
        )

        name = (
            self._profile_name
            .get_text()
            .strip()
        )

        if not name:
            name = profile.name

        return EffectiveProfile(
            id=profile.id,
            name=name,
            mode=self._mode,
            wallpaper=profile.wallpaper,
            appearance=EffectiveAppearance(
                gtk_theme=self._value(
                    self._gtk
                ),
                cinnamon_theme=(
                    resolved
                    .appearance
                    .cinnamon_theme
                ),
                window_borders=self._value(
                    self._borders
                ),
                icon_theme=self._value(
                    self._icons
                ),
                cursor_theme=self._value(
                    self._cursor
                ),
                fonts=FontSettings(
                    interface=(
                        self._font_value(
                            self._interface_font
                        )
                    ),
                    document=(
                        self._font_value(
                            self._document_font
                        )
                    ),
                    monospace=(
                        self._font_value(
                            self._mono_font
                        )
                    ),
                    window_title=(
                        self._font_value(
                            self._title_font
                        )
                    ),
                ),
            ),
        )

    # ---------------------------------------------------------
    # Save / apply
    # ---------------------------------------------------------

    def _save(
        self,
        _: Gtk.Button,
    ) -> None:
        preview = (
            self._build_preview()
        )

        if preview is None:
            return

        if not (
            self._profile_name
            .get_text()
            .strip()
        ):
            self._status.set_text(
                "Profile name cannot be empty."
            )

            return

        self._save_button.set_sensitive(
            False
        )

        self._status.set_text(
            f"Saving {preview.name}..."
        )

        while Gtk.events_pending():
            Gtk.main_iteration_do(
                False
            )

        success = (
            self._on_save(
                preview
            )
        )

        self._save_button.set_sensitive(
            True
        )

        if success:
            self._status.set_text(
                "Profile saved."
            )

        else:
            self._status.set_text(
                "Could not save profile."
            )

    def _apply(
        self,
        _: Gtk.Button,
    ) -> None:
        preview = (
            self._build_preview()
        )

        if preview is None:
            return

        self._apply_button.set_sensitive(
            False
        )

        self._status.set_text(
            f"Applying {preview.name} "
            f"({preview.mode.value})..."
        )

        while Gtk.events_pending():
            Gtk.main_iteration_do(
                False
            )

        success = (
            self._on_apply(
                preview
            )
        )

        self._apply_button.set_sensitive(
            True
        )

        if success:
            self._status.set_text(
                "Applied successfully."
            )

        else:
            self._status.set_text(
                "Apply failed. Check the log."
            )

    # ---------------------------------------------------------
    # Misc
    # ---------------------------------------------------------

    def _refresh_resources(
        self,
        _: Gtk.Button,
    ) -> None:
        self._catalog = (
            ResourceCatalog.discover(
                refresh=True
            )
        )

        self._update_resource_summary()
        self._load_selected_profile()

    def _update_resource_summary(
        self,
    ) -> None:
        self._resource_summary.set_text(
            (
                f"{len(self._catalog.gtk_themes)} GTK themes · "
                f"{len(self._catalog.icon_themes)} icon themes · "
                f"{len(self._catalog.cursor_themes)} cursor themes · "
                f"{len(self._catalog.font_families)} fonts"
            )
        )

    def _update_font_preview(
        self,
        *_: object,
    ) -> None:
        value = self._font_value(
            self._interface_font
        )

        self._font_preview.override_font(
            (
                Pango.FontDescription
                .from_string(
                    value
                )
            )
            if value
            else None
        )

    def _hide_on_close(
        self,
        *_: object,
    ) -> bool:
        self.hide()

        return True