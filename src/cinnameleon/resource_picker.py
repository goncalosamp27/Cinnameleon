"""Visual resource pickers for Cinnameleon."""

from __future__ import annotations

from collections.abc import Sequence

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import (
    Gdk,
    GdkPixbuf,
    GLib,
    Gtk,
    Pango,
)

class GtkThemePickerDialog(Gtk.Dialog):
    """Browse installed GTK themes with a live process-only preview."""

    def __init__(
        self,
        *,
        parent: Gtk.Window,
        themes: Sequence[str],
        current: str | None,
    ) -> None:
        super().__init__(
            title="Choose GTK Theme",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL,
        )

        self.set_default_size(
            820,
            560,
        )

        self.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        self.add_button(
            "Choose",
            Gtk.ResponseType.OK,
        )

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            False,
        )

        self._settings = (
            Gtk.Settings.get_default()
        )

        self._original_theme: str | None = None

        if self._settings is not None:
            self._original_theme = (
                self._settings.get_property(
                    "gtk-theme-name"
                )
            )

        self._selected_theme: str | None = None

        self._search = Gtk.SearchEntry()

        self._list = Gtk.ListBox()

        self._list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )

        self._list.set_activate_on_single_click(
            False
        )

        self._list.set_filter_func(
            self._filter_row
        )

        self._list.connect(
            "row-selected",
            self._on_row_selected,
        )

        self._list.connect(
            "row-activated",
            self._on_row_activated,
        )

        self._search.connect(
            "search-changed",
            self._on_search_changed,
        )

        self._theme_title = Gtk.Label()

        self._theme_title.set_xalign(
            0
        )

        self._theme_title.set_markup(
            "<b>Theme preview</b>"
        )

        self._build_ui(
            themes,
            current,
        )

    def _build_ui(
        self,
        themes: Sequence[str],
        current: str | None,
    ) -> None:
        content = self.get_content_area()

        content.set_border_width(
            16
        )

        content.set_spacing(
            12
        )

        description = Gtk.Label(
            label=(
                "Selecting a theme previews it only "
                "inside Cinnameleon. Your desktop is "
                "not changed until you press Apply."
            )
        )

        description.set_xalign(
            0
        )

        description.set_line_wrap(
            True
        )

        content.pack_start(
            description,
            False,
            False,
            0,
        )

        root = Gtk.Paned.new(
            Gtk.Orientation.HORIZONTAL
        )

        root.set_position(
            280
        )

        content.pack_start(
            root,
            True,
            True,
            0,
        )

        # -----------------------------------------------------
        # Left side
        # -----------------------------------------------------

        left = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )

        left.set_margin_right(
            12
        )

        self._search.set_placeholder_text(
            "Search GTK themes…"
        )

        left.pack_start(
            self._search,
            False,
            False,
            0,
        )

        list_scroll = Gtk.ScrolledWindow()

        list_scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )

        list_scroll.add(
            self._list
        )

        left.pack_start(
            list_scroll,
            True,
            True,
            0,
        )

        root.pack1(
            left,
            resize=False,
            shrink=False,
        )

        current_row: Gtk.ListBoxRow | None = None
        first_row: Gtk.ListBoxRow | None = None

        for theme in themes:
            row = Gtk.ListBoxRow()

            row.resource_name = theme

            container = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=2,
            )

            container.set_border_width(
                8
            )

            name = Gtk.Label(
                label=theme
            )

            name.set_xalign(
                0
            )

            container.pack_start(
                name,
                False,
                False,
                0,
            )

            row.add(
                container
            )

            self._list.add(
                row
            )

            if first_row is None:
                first_row = row

            if theme == current:
                current_row = row

        # -----------------------------------------------------
        # Right side
        # -----------------------------------------------------

        preview = self._build_preview()

        root.pack2(
            preview,
            resize=True,
            shrink=False,
        )

        self.show_all()

        row_to_select = (
            current_row
            or first_row
        )

        if row_to_select is not None:
            self._list.select_row(
                row_to_select
            )

    def _build_preview(
        self,
    ) -> Gtk.Widget:
        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )

        outer.set_margin_left(
            16
        )

        outer.set_margin_right(
            8
        )

        outer.pack_start(
            self._theme_title,
            False,
            False,
            0,
        )

        frame = Gtk.Frame(
            label="Cinnameleon UI Preview"
        )

        outer.pack_start(
            frame,
            False,
            False,
            0,
        )

        demo = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
        )

        demo.set_border_width(
            18
        )

        heading = Gtk.Label()

        heading.set_markup(
            "<big><b>Profile preview</b></big>"
        )

        heading.set_xalign(
            0
        )

        demo.pack_start(
            heading,
            False,
            False,
            0,
        )

        subtitle = Gtk.Label(
            label=(
                "This is how common GTK controls "
                "look with the selected theme."
            )
        )

        subtitle.set_xalign(
            0
        )

        subtitle.set_line_wrap(
            True
        )

        demo.pack_start(
            subtitle,
            False,
            False,
            0,
        )

        entry = Gtk.Entry()

        entry.set_text(
            "Cinnameleon"
        )

        demo.pack_start(
            entry,
            False,
            False,
            0,
        )

        checks = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=18,
        )

        check = Gtk.CheckButton(
            label="Enable profile"
        )

        check.set_active(
            True
        )

        checks.pack_start(
            check,
            False,
            False,
            0,
        )

        switch = Gtk.Switch()

        switch.set_active(
            True
        )

        checks.pack_start(
            switch,
            False,
            False,
            0,
        )

        demo.pack_start(
            checks,
            False,
            False,
            0,
        )

        scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL,
            0,
            100,
            1,
        )

        scale.set_value(
            64
        )

        demo.pack_start(
            scale,
            False,
            False,
            0,
        )

        progress = Gtk.ProgressBar()

        progress.set_fraction(
            0.68
        )

        progress.set_text(
            "68%"
        )

        progress.set_show_text(
            True
        )

        demo.pack_start(
            progress,
            False,
            False,
            0,
        )

        actions = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        normal_button = Gtk.Button(
            label="Cancel"
        )

        actions.pack_end(
            normal_button,
            False,
            False,
            0,
        )

        primary_button = Gtk.Button(
            label="Apply"
        )

        primary_button.get_style_context().add_class(
            "suggested-action"
        )

        actions.pack_end(
            primary_button,
            False,
            False,
            0,
        )

        demo.pack_start(
            actions,
            False,
            False,
            0,
        )

        frame.add(
            demo
        )

        tip = Gtk.Label(
            label=(
                "Tip: double-click a theme in the "
                "list to choose it immediately."
            )
        )

        tip.set_xalign(
            0
        )

        tip.set_line_wrap(
            True
        )

        outer.pack_start(
            tip,
            False,
            False,
            0,
        )

        return outer

    def _filter_row(
        self,
        row: Gtk.ListBoxRow,
    ) -> bool:
        query = (
            self._search
            .get_text()
            .strip()
            .casefold()
        )

        if not query:
            return True

        name = getattr(
            row,
            "resource_name",
            "",
        )

        return query in name.casefold()

    def _on_search_changed(
        self,
        _: Gtk.SearchEntry,
    ) -> None:
        self._list.invalidate_filter()

    def _on_row_selected(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if row is None:
            self._selected_theme = None

            self.set_response_sensitive(
                Gtk.ResponseType.OK,
                False,
            )

            return

        theme = getattr(
            row,
            "resource_name",
            None,
        )

        if not isinstance(
            theme,
            str,
        ):
            return

        self._selected_theme = theme

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            True,
        )

        self._theme_title.set_text(
            theme
        )

        self._theme_title.set_text(
            theme
        )

        if self._settings is not None:
            self._settings.set_property(
                "gtk-theme-name",
                theme,
            )

    def _on_row_activated(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        self._list.select_row(
            row
        )

        self.response(
            Gtk.ResponseType.OK
        )

    def _restore_original_theme(
        self,
    ) -> None:
        if (
            self._settings is not None
            and self._original_theme
        ):
            self._settings.set_property(
                "gtk-theme-name",
                self._original_theme,
            )

    def choose(
        self,
    ) -> str | None:
        response = self.run()

        selected = (
            self._selected_theme
            if response
            == Gtk.ResponseType.OK
            else None
        )

        self._restore_original_theme()

        self.destroy()

        return selected


class FontPickerDialog(Gtk.Dialog):
    """Browse installed font families with visual samples."""

    SAMPLE = (
        "Aa Bb Cc 0123 — "
        "The quick brown fox"
    )

    def __init__(
        self,
        *,
        parent: Gtk.Window,
        fonts: Sequence[str],
        current: str | None,
    ) -> None:
        super().__init__(
            title="Choose Font",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL,
        )

        self.set_default_size(
            760,
            580,
        )

        self.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        self.add_button(
            "Choose",
            Gtk.ResponseType.OK,
        )

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            False,
        )

        self._selected_font: str | None = None

        self._search = Gtk.SearchEntry()

        self._list = Gtk.ListBox()

        self._list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )

        self._list.set_activate_on_single_click(
            False
        )

        self._list.set_filter_func(
            self._filter_row
        )

        self._list.connect(
            "row-selected",
            self._on_row_selected,
        )

        self._list.connect(
            "row-activated",
            self._on_row_activated,
        )

        self._search.connect(
            "search-changed",
            self._on_search_changed,
        )

        self._preview_name = Gtk.Label()

        self._preview_name.set_xalign(
            0
        )

        self._preview_sample = Gtk.Label(
            label=(
                "The quick brown fox jumps over "
                "the lazy dog.\n"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
                "abcdefghijklmnopqrstuvwxyz\n"
                "0123456789 !@#$%^&*()"
            )
        )

        self._preview_sample.set_xalign(
            0
        )

        self._preview_sample.set_line_wrap(
            True
        )

        self._build_ui(
            fonts,
            current,
        )

    def _build_ui(
        self,
        fonts: Sequence[str],
        current: str | None,
    ) -> None:
        content = self.get_content_area()

        content.set_border_width(
            16
        )

        content.set_spacing(
            12
        )

        self._search.set_placeholder_text(
            "Search fonts…"
        )

        content.pack_start(
            self._search,
            False,
            False,
            0,
        )

        root = Gtk.Paned.new(
            Gtk.Orientation.HORIZONTAL
        )

        root.set_position(
            390
        )

        content.pack_start(
            root,
            True,
            True,
            0,
        )

        scroll = Gtk.ScrolledWindow()

        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )

        scroll.add(
            self._list
        )

        root.pack1(
            scroll,
            resize=True,
            shrink=False,
        )

        preview = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )

        preview.set_border_width(
            18
        )

        title = Gtk.Label()

        title.set_markup(
            "<b>Font Preview</b>"
        )

        title.set_xalign(
            0
        )

        preview.pack_start(
            title,
            False,
            False,
            0,
        )

        preview.pack_start(
            self._preview_name,
            False,
            False,
            0,
        )

        separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        preview.pack_start(
            separator,
            False,
            False,
            0,
        )

        preview.pack_start(
            self._preview_sample,
            False,
            False,
            0,
        )

        root.pack2(
            preview,
            resize=True,
            shrink=False,
        )

        current_row: Gtk.ListBoxRow | None = None
        first_row: Gtk.ListBoxRow | None = None

        for family in fonts:
            row = Gtk.ListBoxRow()

            row.resource_name = family

            container = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=4,
            )

            container.set_border_width(
                10
            )

            name = Gtk.Label(
                label=family
            )

            name.set_xalign(
                0
            )

            container.pack_start(
                name,
                False,
                False,
                0,
            )

            sample = Gtk.Label(
                label=self.SAMPLE
            )

            sample.set_xalign(
                0
            )

            sample.set_ellipsize(
                Pango.EllipsizeMode.END
            )

            sample.override_font(
                Pango.FontDescription.from_string(
                    f"{family} 12"
                )
            )

            container.pack_start(
                sample,
                False,
                False,
                0,
            )

            row.add(
                container
            )

            self._list.add(
                row
            )

            if first_row is None:
                first_row = row

            if family == current:
                current_row = row

        self.show_all()

        row_to_select = (
            current_row
            or first_row
        )

        if row_to_select is not None:
            self._list.select_row(
                row_to_select
            )

    def _filter_row(
        self,
        row: Gtk.ListBoxRow,
    ) -> bool:
        query = (
            self._search
            .get_text()
            .strip()
            .casefold()
        )

        if not query:
            return True

        name = getattr(
            row,
            "resource_name",
            "",
        )

        return query in name.casefold()

    def _on_search_changed(
        self,
        _: Gtk.SearchEntry,
    ) -> None:
        self._list.invalidate_filter()

    def _on_row_selected(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if row is None:
            self._selected_font = None

            self.set_response_sensitive(
                Gtk.ResponseType.OK,
                False,
            )

            return

        family = getattr(
            row,
            "resource_name",
            None,
        )

        if not isinstance(
            family,
            str,
        ):
            return

        self._selected_font = family

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            True,
        )

        self._preview_name.set_markup(
            f"<big><b>{family}</b></big>"
        )

        self._preview_sample.override_font(
            Pango.FontDescription.from_string(
                f"{family} 16"
            )
        )

    def _on_row_activated(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        self._list.select_row(
            row
        )

        self.response(
            Gtk.ResponseType.OK
        )

    def choose(
        self,
    ) -> str | None:
        response = self.run()

        selected = (
            self._selected_font
            if response
            == Gtk.ResponseType.OK
            else None
        )

        self.destroy()

        return selected

class IconThemePickerDialog(Gtk.Dialog):
    """Browse installed icon themes with real icon previews."""

    ICONS = (
        ("folder", "Folder"),
        ("document-open", "Open"),
        ("document-save", "Save"),
        ("utilities-terminal", "Terminal"),
        ("preferences-system", "Settings"),
        ("user-home", "Home"),
        ("edit-copy", "Copy"),
        ("edit-delete", "Trash"),
    )

    def __init__(
        self,
        *,
        parent: Gtk.Window,
        themes: Sequence[str],
        current: str | None,
    ) -> None:
        super().__init__(
            title="Choose Icon Theme",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL,
        )

        self.set_default_size(
            820,
            560,
        )

        self.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        self.add_button(
            "Choose",
            Gtk.ResponseType.OK,
        )

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            False,
        )

        self._selected_theme: str | None = None

        self._search = Gtk.SearchEntry()
        self._list = Gtk.ListBox()

        self._list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )

        self._list.set_activate_on_single_click(
            False
        )

        self._list.set_filter_func(
            self._filter_row
        )

        self._list.connect(
            "row-selected",
            self._on_row_selected,
        )

        self._list.connect(
            "row-activated",
            self._on_row_activated,
        )

        self._search.connect(
            "search-changed",
            self._on_search_changed,
        )

        self._preview_title = Gtk.Label()
        self._preview_title.set_xalign(0)

        self._preview_grid = Gtk.Grid(
            column_spacing=20,
            row_spacing=20,
        )

        self._build_ui(
            themes,
            current,
        )

    def _build_ui(
        self,
        themes: Sequence[str],
        current: str | None,
    ) -> None:
        content = self.get_content_area()

        content.set_border_width(16)
        content.set_spacing(12)

        root = Gtk.Paned.new(
            Gtk.Orientation.HORIZONTAL
        )

        root.set_position(280)

        content.pack_start(
            root,
            True,
            True,
            0,
        )

        # Left

        left = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )

        left.set_margin_right(12)

        self._search.set_placeholder_text(
            "Search icon themes…"
        )

        left.pack_start(
            self._search,
            False,
            False,
            0,
        )

        scroll = Gtk.ScrolledWindow()

        scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )

        scroll.add(
            self._list
        )

        left.pack_start(
            scroll,
            True,
            True,
            0,
        )

        root.pack1(
            left,
            resize=False,
            shrink=False,
        )

        current_row = None
        first_row = None

        for theme in themes:
            row = Gtk.ListBoxRow()
            row.resource_name = theme

            label = Gtk.Label(
                label=theme
            )

            label.set_xalign(0)
            label.set_margin_top(10)
            label.set_margin_bottom(10)
            label.set_margin_start(10)
            label.set_margin_end(10)

            row.add(label)

            self._list.add(row)

            if first_row is None:
                first_row = row

            if theme == current:
                current_row = row

        # Right

        right = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )

        right.set_margin_left(18)
        right.set_margin_right(8)

        title = Gtk.Label()

        title.set_markup(
            "<b>Icon Preview</b>"
        )

        title.set_xalign(0)

        right.pack_start(
            title,
            False,
            False,
            0,
        )

        right.pack_start(
            self._preview_title,
            False,
            False,
            0,
        )

        frame = Gtk.Frame()

        frame.set_shadow_type(
            Gtk.ShadowType.IN
        )

        preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )

        preview_box.set_border_width(24)

        preview_box.pack_start(
            self._preview_grid,
            False,
            False,
            0,
        )

        frame.add(
            preview_box
        )

        right.pack_start(
            frame,
            False,
            False,
            0,
        )

        tip = Gtk.Label(
            label=(
                "These icons are loaded directly "
                "from the selected icon theme."
            )
        )

        tip.set_xalign(0)
        tip.set_line_wrap(True)

        right.pack_start(
            tip,
            False,
            False,
            0,
        )

        root.pack2(
            right,
            resize=True,
            shrink=False,
        )

        self.show_all()

        selected = (
            current_row
            or first_row
        )

        if selected is not None:
            self._list.select_row(
                selected
            )

    def _create_icon_theme(
        self,
        name: str,
    ) -> Gtk.IconTheme:
        theme = Gtk.IconTheme.new()

        screen = Gdk.Screen.get_default()

        if screen is not None:
            theme.set_screen(
                screen
            )

        theme.set_custom_theme(
            name
        )

        return theme

    @staticmethod
    def _load_icon(
        theme: Gtk.IconTheme,
        name: str,
        size: int,
    ) -> GdkPixbuf.Pixbuf | None:
        candidates = (
            name,
            f"{name}-symbolic",
        )

        for candidate in candidates:
            try:
                return theme.load_icon(
                    candidate,
                    size,
                    Gtk.IconLookupFlags.FORCE_SIZE,
                )

            except GLib.Error:
                continue

        return None

    def _update_preview(
        self,
        theme_name: str,
    ) -> None:
        for child in (
            self._preview_grid.get_children()
        ):
            self._preview_grid.remove(
                child
            )

        self._preview_title.set_text(
            theme_name
        )

        theme = self._create_icon_theme(
            theme_name
        )

        for index, (
            icon_name,
            label_text,
        ) in enumerate(self.ICONS):
            card = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
            )

            card.set_size_request(
                90,
                90,
            )

            pixbuf = self._load_icon(
                theme,
                icon_name,
                40,
            )

            if pixbuf is not None:
                image = Gtk.Image.new_from_pixbuf(
                    pixbuf
                )

            else:
                image = Gtk.Image.new_from_icon_name(
                    "image-missing",
                    Gtk.IconSize.DIALOG,
                )

            card.pack_start(
                image,
                False,
                False,
                0,
            )

            label = Gtk.Label(
                label=label_text
            )

            card.pack_start(
                label,
                False,
                False,
                0,
            )

            column = index % 4
            row = index // 4

            self._preview_grid.attach(
                card,
                column,
                row,
                1,
                1,
            )

        self._preview_grid.show_all()

    def _filter_row(
        self,
        row: Gtk.ListBoxRow,
    ) -> bool:
        query = (
            self._search
            .get_text()
            .strip()
            .casefold()
        )

        if not query:
            return True

        name = getattr(
            row,
            "resource_name",
            "",
        )

        return (
            query
            in name.casefold()
        )

    def _on_search_changed(
        self,
        _: Gtk.SearchEntry,
    ) -> None:
        self._list.invalidate_filter()

    def _on_row_selected(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if row is None:
            self._selected_theme = None

            self.set_response_sensitive(
                Gtk.ResponseType.OK,
                False,
            )

            return

        theme = getattr(
            row,
            "resource_name",
            None,
        )

        if not isinstance(
            theme,
            str,
        ):
            return

        self._selected_theme = theme

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            True,
        )

        self._update_preview(
            theme
        )

    def _on_row_activated(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        self._list.select_row(
            row
        )

        self.response(
            Gtk.ResponseType.OK
        )

    def choose(
        self,
    ) -> str | None:
        response = self.run()

        selected = (
            self._selected_theme
            if response
            == Gtk.ResponseType.OK
            else None
        )

        self.destroy()

        return selected


class CursorThemePickerDialog(Gtk.Dialog):
    """Browse cursor themes with live cursor previews."""

    CURSORS = (
        ("default", "Default"),
        ("pointer", "Pointer"),
        ("text", "Text"),
        ("crosshair", "Crosshair"),
        ("wait", "Wait"),
        ("grab", "Grab"),
    )

    def __init__(
        self,
        *,
        parent: Gtk.Window,
        themes: Sequence[str],
        current: str | None,
    ) -> None:
        super().__init__(
            title="Choose Cursor Theme",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL,
        )

        self.set_default_size(
            820,
            560,
        )

        self.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        self.add_button(
            "Choose",
            Gtk.ResponseType.OK,
        )

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            False,
        )

        self._selected_theme: (
            str | None
        ) = None

        self._settings = (
            Gtk.Settings.get_default()
        )

        self._original_theme: (
            str | None
        ) = None

        if self._settings is not None:
            self._original_theme = (
                self._settings.get_property(
                    "gtk-cursor-theme-name"
                )
            )

        self._search = Gtk.SearchEntry()
        self._list = Gtk.ListBox()

        self._list.set_selection_mode(
            Gtk.SelectionMode.SINGLE
        )

        self._list.set_activate_on_single_click(
            False
        )

        self._list.set_filter_func(
            self._filter_row
        )

        self._list.connect(
            "row-selected",
            self._on_row_selected,
        )

        self._list.connect(
            "row-activated",
            self._on_row_activated,
        )

        self._search.connect(
            "search-changed",
            self._on_search_changed,
        )

        self._preview_title = Gtk.Label()
        self._preview_title.set_xalign(0)

        self._cursor_boxes: list[
            tuple[Gtk.EventBox, str]
        ] = []

        self._build_ui(
            themes,
            current,
        )

    def _build_ui(
        self,
        themes: Sequence[str],
        current: str | None,
    ) -> None:
        content = self.get_content_area()

        content.set_border_width(16)
        content.set_spacing(12)

        root = Gtk.Paned.new(
            Gtk.Orientation.HORIZONTAL
        )

        root.set_position(280)

        content.pack_start(
            root,
            True,
            True,
            0,
        )

        left = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )

        left.set_margin_right(12)

        self._search.set_placeholder_text(
            "Search cursor themes…"
        )

        left.pack_start(
            self._search,
            False,
            False,
            0,
        )

        scroll = Gtk.ScrolledWindow()

        scroll.add(
            self._list
        )

        left.pack_start(
            scroll,
            True,
            True,
            0,
        )

        root.pack1(
            left,
            resize=False,
            shrink=False,
        )

        current_row = None
        first_row = None

        for theme in themes:
            row = Gtk.ListBoxRow()
            row.resource_name = theme

            label = Gtk.Label(
                label=theme
            )

            label.set_xalign(0)

            label.set_margin_top(10)
            label.set_margin_bottom(10)
            label.set_margin_start(10)
            label.set_margin_end(10)

            row.add(label)

            self._list.add(
                row
            )

            if first_row is None:
                first_row = row

            if theme == current:
                current_row = row

        right = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )

        right.set_margin_left(18)

        heading = Gtk.Label()

        heading.set_markup(
            "<b>Cursor Preview</b>"
        )

        heading.set_xalign(0)

        right.pack_start(
            heading,
            False,
            False,
            0,
        )

        right.pack_start(
            self._preview_title,
            False,
            False,
            0,
        )

        description = Gtk.Label(
            label=(
                "Move your mouse over each box "
                "to preview the actual cursor."
            )
        )

        description.set_xalign(0)
        description.set_line_wrap(True)

        right.pack_start(
            description,
            False,
            False,
            0,
        )

        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=12,
        )

        for index, (
            cursor_name,
            label_text,
        ) in enumerate(self.CURSORS):
            event_box = Gtk.EventBox()

            event_box.set_size_request(
                150,
                100,
            )

            frame = Gtk.Frame()

            box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
            )

            box.set_border_width(
                20
            )

            icon = Gtk.Image.new_from_icon_name(
                "input-mouse-symbolic",
                Gtk.IconSize.DIALOG,
            )

            box.pack_start(
                icon,
                False,
                False,
                0,
            )

            label = Gtk.Label(
                label=label_text
            )

            box.pack_start(
                label,
                False,
                False,
                0,
            )

            frame.add(box)
            event_box.add(frame)

            event_box.connect(
                "realize",
                self._cursor_box_realized,
                cursor_name,
            )

            self._cursor_boxes.append(
                (
                    event_box,
                    cursor_name,
                )
            )

            grid.attach(
                event_box,
                index % 2,
                index // 2,
                1,
                1,
            )

        right.pack_start(
            grid,
            False,
            False,
            0,
        )

        root.pack2(
            right,
            resize=True,
            shrink=False,
        )

        self.show_all()

        selected = (
            current_row
            or first_row
        )

        if selected is not None:
            self._list.select_row(
                selected
            )

    def _set_cursor_on_box(
        self,
        event_box: Gtk.EventBox,
        cursor_name: str,
    ) -> None:
        window = event_box.get_window()

        if window is None:
            return

        display = window.get_display()

        try:
            cursor = Gdk.Cursor.new_from_name(
                display,
                cursor_name,
            )

        except Exception:
            cursor = None

        if cursor is not None:
            window.set_cursor(
                cursor
            )

    def _cursor_box_realized(
        self,
        event_box: Gtk.EventBox,
        cursor_name: str,
    ) -> None:
        self._set_cursor_on_box(
            event_box,
            cursor_name,
        )

    def _refresh_cursors(
        self,
    ) -> None:
        for (
            event_box,
            cursor_name,
        ) in self._cursor_boxes:
            self._set_cursor_on_box(
                event_box,
                cursor_name,
            )

    def _apply_preview_theme(
        self,
        theme: str,
    ) -> None:
        self._preview_title.set_text(
            theme
        )

        if self._settings is not None:
            self._settings.set_property(
                "gtk-cursor-theme-name",
                theme,
            )

        self._refresh_cursors()

    def _restore_original_theme(
        self,
    ) -> None:
        if (
            self._settings is not None
            and self._original_theme
        ):
            self._settings.set_property(
                "gtk-cursor-theme-name",
                self._original_theme,
            )

        self._refresh_cursors()

    def _filter_row(
        self,
        row: Gtk.ListBoxRow,
    ) -> bool:
        query = (
            self._search
            .get_text()
            .strip()
            .casefold()
        )

        if not query:
            return True

        name = getattr(
            row,
            "resource_name",
            "",
        )

        return (
            query
            in name.casefold()
        )

    def _on_search_changed(
        self,
        _: Gtk.SearchEntry,
    ) -> None:
        self._list.invalidate_filter()

    def _on_row_selected(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if row is None:
            self._selected_theme = None

            self.set_response_sensitive(
                Gtk.ResponseType.OK,
                False,
            )

            return

        theme = getattr(
            row,
            "resource_name",
            None,
        )

        if not isinstance(
            theme,
            str,
        ):
            return

        self._selected_theme = theme

        self.set_response_sensitive(
            Gtk.ResponseType.OK,
            True,
        )

        self._apply_preview_theme(
            theme
        )

    def _on_row_activated(
        self,
        _: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        self._list.select_row(
            row
        )

        self.response(
            Gtk.ResponseType.OK
        )

    def choose(
        self,
    ) -> str | None:
        response = self.run()

        selected = (
            self._selected_theme
            if response
            == Gtk.ResponseType.OK
            else None
        )

        self._restore_original_theme()

        self.destroy()

        return selected