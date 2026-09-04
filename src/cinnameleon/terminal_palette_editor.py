"""Visual terminal palette editor using a real VTE terminal."""

from __future__ import annotations

import getpass
import socket

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")

from gi.repository import Gdk, Gtk, Vte

from cinnameleon.models import (
    ANSI_COLOR_KEYS,
    TerminalPalette,
)
from cinnameleon.terminal_backend import (
    DEFAULT_TERMINAL_PALETTE,
    GnomeTerminalBackend,
    TerminalBackendError,
)


ANSI_LABELS = (
    "Black",
    "Red",
    "Green",
    "Yellow",
    "Blue",
    "Magenta",
    "Cyan",
    "White",
    "Bright Black",
    "Bright Red",
    "Bright Green",
    "Bright Yellow",
    "Bright Blue",
    "Bright Magenta",
    "Bright Cyan",
    "Bright White",
)


ANSI_CODES = (
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "90",
    "91",
    "92",
    "93",
    "94",
    "95",
    "96",
    "97",
)


class TerminalPaletteEditor(Gtk.Box):
    """Edit a terminal palette with an actual VTE preview."""

    def __init__(
        self,
    ) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )

        self._backend = (
            GnomeTerminalBackend()
        )

        self._loading = False

        self._special_buttons: dict[
            str,
            Gtk.ColorButton,
        ] = {}

        self._ansi_buttons: list[
            Gtk.ColorButton
        ] = []

        self._build_ui()

        self.load_palette(
            None
        )

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(
        self,
    ) -> None:
        self._build_heading()
        self._build_actions()

        self._controls = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
        )

        self.pack_start(
            self._controls,
            False,
            False,
            0,
        )

        self._build_main_colors()
        self._build_ansi_colors()
        self._build_preview()

    def _build_heading(
        self,
    ) -> None:
        heading = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )

        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
        )

        title = Gtk.Label()

        title.set_markup(
            "<b>Terminal palette</b>"
        )

        title.set_xalign(
            0
        )

        title_box.pack_start(
            title,
            False,
            False,
            0,
        )

        self._target_label = Gtk.Label(
            label=(
                self._backend
                .describe_target()
            )
        )

        self._target_label.set_xalign(
            0
        )

        title_box.pack_start(
            self._target_label,
            False,
            False,
            0,
        )

        heading.pack_start(
            title_box,
            True,
            True,
            0,
        )

        label = Gtk.Label(
            label="Manage"
        )

        heading.pack_end(
            label,
            False,
            False,
            0,
        )

        self._enabled = Gtk.Switch()

        self._enabled.connect(
            "notify::active",
            self._enabled_changed,
        )

        heading.pack_end(
            self._enabled,
            False,
            False,
            0,
        )

        self.pack_start(
            heading,
            False,
            False,
            0,
        )

    def _build_actions(
        self,
    ) -> None:
        actions = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        self._capture = Gtk.Button(
            label=(
                "Capture current "
                "terminal palette"
            )
        )

        self._capture.set_sensitive(
            self._backend.is_available()
        )

        self._capture.connect(
            "clicked",
            self._capture_current,
        )

        actions.pack_start(
            self._capture,
            False,
            False,
            0,
        )

        self._status = Gtk.Label()

        self._status.set_xalign(
            0
        )

        actions.pack_start(
            self._status,
            True,
            True,
            0,
        )

        self.pack_start(
            actions,
            False,
            False,
            0,
        )

    # =========================================================
    # Main colors
    # =========================================================

    def _build_main_colors(
        self,
    ) -> None:
        frame = Gtk.Frame(
            label="Main colors"
        )

        grid = Gtk.Grid(
            column_spacing=14,
            row_spacing=8,
        )

        grid.set_border_width(
            12
        )

        frame.add(
            grid
        )

        values = (
            (
                "background",
                "Background",
            ),
            (
                "foreground",
                "Foreground",
            ),
            (
                "cursor",
                "Cursor",
            ),
            (
                "selection_background",
                "Selection background",
            ),
            (
                "selection_foreground",
                "Selection foreground",
            ),
        )

        for row, (
            key,
            title,
        ) in enumerate(values):
            label = Gtk.Label(
                label=title
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

            button = (
                self._create_color_button(
                    title
                )
            )

            button.set_size_request(
                60,
                32,
            )

            self._special_buttons[
                key
            ] = button

            grid.attach(
                button,
                1,
                row,
                1,
                1,
            )

            value_label = Gtk.Label()

            value_label.set_xalign(
                0
            )

            button._hex_label = (
                value_label
            )

            grid.attach(
                value_label,
                2,
                row,
                1,
                1,
            )

        self._controls.pack_start(
            frame,
            False,
            False,
            0,
        )

    # =========================================================
    # ANSI colors
    # =========================================================

    def _build_ansi_colors(
        self,
    ) -> None:
        frame = Gtk.Frame(
            label="ANSI 16 colors"
        )

        grid = Gtk.Grid(
            column_spacing=8,
            row_spacing=12,
        )

        grid.set_border_width(
            12
        )

        frame.add(
            grid
        )

        for index, (
            name,
            code,
        ) in enumerate(
            zip(
                ANSI_LABELS,
                ANSI_CODES,
                strict=True,
            )
        ):
            cell = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=3,
            )

            button = (
                self._create_color_button(
                    name
                )
            )

            button.set_size_request(
                64,
                38,
            )

            self._ansi_buttons.append(
                button
            )

            cell.pack_start(
                button,
                False,
                False,
                0,
            )

            label = Gtk.Label(
                label=name
            )

            label.set_line_wrap(
                True
            )

            label.set_max_width_chars(
                12
            )

            cell.pack_start(
                label,
                False,
                False,
                0,
            )

            if index < 8:
                semantic = (
                    f"ANSI {index} · {code}"
                )

            else:
                semantic = (
                    f"ANSI {index} · {code}"
                )

            semantic_label = Gtk.Label(
                label=semantic
            )

            cell.pack_start(
                semantic_label,
                False,
                False,
                0,
            )

            hex_label = Gtk.Label()

            button._hex_label = (
                hex_label
            )

            cell.pack_start(
                hex_label,
                False,
                False,
                0,
            )

            grid.attach(
                cell,
                index % 8,
                index // 8,
                1,
                1,
            )

        self._controls.pack_start(
            frame,
            False,
            False,
            0,
        )

    # =========================================================
    # REAL VTE preview
    # =========================================================

    def _build_preview(
        self,
    ) -> None:
        frame = Gtk.Frame(
            label="Real terminal preview"
        )

        preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )

        preview_box.set_border_width(
            8
        )

        explanation = Gtk.Label(
            label=(
                "Rendered by VTE using real ANSI "
                "escape sequences."
            )
        )

        explanation.set_xalign(
            0
        )

        preview_box.pack_start(
            explanation,
            False,
            False,
            0,
        )

        self._terminal = Vte.Terminal()

        self._terminal.set_size(
            90,
            15,
        )

        self._terminal.set_scrollback_lines(
            0
        )

        self._terminal.set_input_enabled(
            False
        )

        self._terminal.set_cursor_shape(
            Vte.CursorShape.BLOCK
        )

        self._terminal.set_cursor_blink_mode(
            Vte.CursorBlinkMode.OFF
        )

        self._terminal.set_audible_bell(
            False
        )

        self._terminal.set_mouse_autohide(
            False
        )

        preview_box.pack_start(
            self._terminal,
            False,
            False,
            0,
        )

        legend = Gtk.Label(
            label=(
                "Linux Mint / Bash preview: "
                "user@host normally uses 1;32 "
                "(bold green) and ~ uses 1;34 "
                "(bold blue)."
            )
        )

        legend.set_xalign(
            0
        )

        legend.set_line_wrap(
            True
        )

        preview_box.pack_start(
            legend,
            False,
            False,
            0,
        )

        frame.add(
            preview_box
        )

        self._controls.pack_start(
            frame,
            False,
            False,
            0,
        )

    # =========================================================
    # Color helpers
    # =========================================================

    def _create_color_button(
        self,
        title: str,
    ) -> Gtk.ColorButton:
        button = Gtk.ColorButton()

        button.set_title(
            title
        )

        button.set_use_alpha(
            False
        )

        button.connect(
            "color-set",
            self._color_changed,
        )

        return button

    @staticmethod
    def _rgba(
        color: str,
    ) -> Gdk.RGBA:
        rgba = Gdk.RGBA()

        if not rgba.parse(
            color
        ):
            rgba.parse(
                "#000000"
            )

        return rgba

    @staticmethod
    def _hex(
        button: Gtk.ColorButton,
    ) -> str:
        rgba = button.get_rgba()

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

    def _set_button(
        self,
        button: Gtk.ColorButton,
        color: str,
    ) -> None:
        button.set_rgba(
            self._rgba(
                color
            )
        )

        self._update_button_label(
            button
        )

    def _update_button_label(
        self,
        button: Gtk.ColorButton,
    ) -> None:
        label = getattr(
            button,
            "_hex_label",
            None,
        )

        if label is None:
            return

        label.set_text(
            self._hex(
                button
            )
        )

    # =========================================================
    # Palette
    # =========================================================

    def _set_palette_values(
        self,
        palette: TerminalPalette,
    ) -> None:
        self._set_button(
            self._special_buttons[
                "background"
            ],
            palette.background,
        )

        self._set_button(
            self._special_buttons[
                "foreground"
            ],
            palette.foreground,
        )

        self._set_button(
            self._special_buttons[
                "cursor"
            ],
            palette.cursor,
        )

        self._set_button(
            self._special_buttons[
                "selection_background"
            ],
            palette.selection_background,
        )

        self._set_button(
            self._special_buttons[
                "selection_foreground"
            ],
            palette.selection_foreground,
        )

        for button, color in zip(
            self._ansi_buttons,
            palette.ansi,
            strict=True,
        ):
            self._set_button(
                button,
                color,
            )

    def _palette_from_controls(
        self,
    ) -> TerminalPalette:
        return TerminalPalette(
            background=self._hex(
                self._special_buttons[
                    "background"
                ]
            ),
            foreground=self._hex(
                self._special_buttons[
                    "foreground"
                ]
            ),
            cursor=self._hex(
                self._special_buttons[
                    "cursor"
                ]
            ),
            selection_background=(
                self._hex(
                    self._special_buttons[
                        "selection_background"
                    ]
                )
            ),
            selection_foreground=(
                self._hex(
                    self._special_buttons[
                        "selection_foreground"
                    ]
                )
            ),
            ansi=tuple(
                self._hex(
                    button
                )
                for button
                in self._ansi_buttons
            ),
        )

    def palette(
        self,
    ) -> TerminalPalette | None:
        if not self._enabled.get_active():
            return None

        return self._palette_from_controls()

    def load_palette(
        self,
        palette: TerminalPalette | None,
    ) -> None:
        self._loading = True

        try:
            if palette is None:
                try:
                    loaded = (
                        self._backend
                        .read_palette()
                    )

                except TerminalBackendError:
                    loaded = (
                        DEFAULT_TERMINAL_PALETTE
                    )

                self._set_palette_values(
                    loaded
                )

                self._enabled.set_active(
                    False
                )

            else:
                self._set_palette_values(
                    palette
                )

                self._enabled.set_active(
                    True
                )

        finally:
            self._loading = False

        self._update_sensitivity()
        self._update_preview()

    # =========================================================
    # VTE palette
    # =========================================================

    def _configure_vte_palette(
        self,
        palette: TerminalPalette,
    ) -> None:
        foreground = self._rgba(
            palette.foreground
        )

        background = self._rgba(
            palette.background
        )

        ansi = [
            self._rgba(color)
            for color
            in palette.ansi
        ]

        self._terminal.set_colors(
            foreground,
            background,
            ansi,
        )

        self._terminal.set_color_cursor(
            self._rgba(
                palette.cursor
            )
        )

        self._terminal.set_color_cursor_foreground(
            background
        )

        self._terminal.set_color_highlight(
            self._rgba(
                palette.selection_background
            )
        )

        self._terminal.set_color_highlight_foreground(
            self._rgba(
                palette.selection_foreground
            )
        )

        try:
            bold_is_bright = (
                self._backend
                .bold_is_bright()
            )

        except Exception:
            bold_is_bright = True

        self._terminal.set_bold_is_bright(
            bold_is_bright
        )

    # =========================================================
    # Real ANSI content
    # =========================================================

    @staticmethod
    def _prompt(
        username: str,
        hostname: str,
        *,
        command: str = "",
    ) -> str:
        """
        Typical Ubuntu/Linux Mint Bash prompt.

        1;32 = bold green
        1;34 = bold blue

        With bold-is-bright enabled these map to
        ANSI 10 and ANSI 12 respectively.
        """

        return (
            "\x1b[01;32m"
            f"{username}@{hostname}"
            "\x1b[00m"
            ":"
            "\x1b[01;34m"
            "~"
            "\x1b[00m"
            "$ "
            f"{command}"
        )

    def _preview_text(
        self,
    ) -> bytes:
        username = (
            getpass.getuser()
        )

        hostname = (
            socket.gethostname()
        )

        lines: list[str] = []

        # -----------------------------------------------------
        # Exact style of the user's real Bash terminal
        # -----------------------------------------------------

        lines.append(
            self._prompt(
                username,
                hostname,
                command="yesss",
            )
        )

        lines.append(
            "yesss: command not found"
        )

        lines.append("")

        # -----------------------------------------------------
        # Explain what affects the actual prompt
        # -----------------------------------------------------

        lines.append(
            "\x1b[1;32m"
            "user@host"
            "\x1b[0m"
            " = 1;32 bold green"
            "  |  "
            "\x1b[1;34m"
            "~"
            "\x1b[0m"
            " = 1;34 bold blue"
        )

        lines.append("")

        # -----------------------------------------------------
        # Standard ANSI 0-7
        # -----------------------------------------------------

        standard: list[str] = []

        for index in range(8):
            code = 30 + index

            standard.append(
                f"\x1b[{code}m"
                f" {index:02d} "
                "\x1b[0m"
            )

        lines.append(
            "ANSI:   "
            + " ".join(
                standard
            )
        )

        # -----------------------------------------------------
        # Actual bold mapping
        # This is the key part for Mint's PS1.
        # -----------------------------------------------------

        bold: list[str] = []

        for index in range(8):
            code = 30 + index

            bold.append(
                f"\x1b[1;{code}m"
                f" {index + 8:02d} "
                "\x1b[0m"
            )

        lines.append(
            "Bold:   "
            + " ".join(
                bold
            )
        )

        # -----------------------------------------------------
        # Direct bright ANSI codes
        # -----------------------------------------------------

        bright: list[str] = []

        for index in range(8):
            code = 90 + index

            bright.append(
                f"\x1b[{code}m"
                f" {index + 8:02d} "
                "\x1b[0m"
            )

        lines.append(
            "Bright: "
            + " ".join(
                bright
            )
        )

        lines.append("")

        # -----------------------------------------------------
        # Leave cursor at the end of a real prompt
        # -----------------------------------------------------

        content = (
            "\r\n".join(lines)
            + "\r\n"
            + self._prompt(
                username,
                hostname,
            )
        )

        return content.encode(
            "utf-8"
        )

    def _update_preview(
        self,
    ) -> None:
        palette = (
            self._palette_from_controls()
        )

        self._configure_vte_palette(
            palette
        )

        self._terminal.reset(
            True,
            True,
        )

        self._terminal.feed(
            self._preview_text()
        )

    # =========================================================
    # Events
    # =========================================================

    def _enabled_changed(
        self,
        _: Gtk.Switch,
        __: object,
    ) -> None:
        if self._loading:
            return

        self._update_sensitivity()
        self._update_preview()

    def _update_sensitivity(
        self,
    ) -> None:
        self._controls.set_sensitive(
            self._enabled.get_active()
        )

    def _capture_current(
        self,
        _: Gtk.Button,
    ) -> None:
        try:
            palette = (
                self._backend
                .read_palette()
            )

        except TerminalBackendError as error:
            self._status.set_text(
                str(error)
            )

            return

        self._loading = True

        try:
            self._set_palette_values(
                palette
            )

            self._enabled.set_active(
                True
            )

        finally:
            self._loading = False

        self._update_sensitivity()
        self._update_preview()

        self._status.set_text(
            "Current terminal palette captured."
        )

    def _color_changed(
        self,
        button: Gtk.ColorButton,
    ) -> None:
        self._update_button_label(
            button
        )

        self._update_preview()