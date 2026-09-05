"""Read and apply Cinnamon appearance settings through Gio.Settings."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio

from cinnameleon.models import EffectiveProfile

from cinnameleon.resources import (
    cinnamon_theme_exists,
    cursor_theme_exists,
    gtk_theme_exists,
    icon_theme_exists,
    window_border_theme_exists,
)
from cinnameleon.validator import font_exists

from cinnameleon.snapshot import (
    SettingsSnapshot,
    SnapshotEntry,
)


BACKGROUND_SCHEMA = "org.cinnamon.desktop.background"
INTERFACE_SCHEMA = "org.cinnamon.desktop.interface"
CINNAMON_THEME_SCHEMA = "org.cinnamon.theme"
WINDOW_MANAGER_SCHEMA = "org.cinnamon.desktop.wm.preferences"
GNOME_INTERFACE_SCHEMA = "org.gnome.desktop.interface"


class SettingsBackendError(RuntimeError):
    """Raised when a system appearance setting cannot be accessed."""


@dataclass(frozen=True)
class SettingTarget:
    """A desired value for one GSettings key."""

    label: str
    schema_id: str
    key: str
    value: str


@dataclass(frozen=True)
class SettingChange:
    """Comparison between the current and desired setting value."""

    label: str
    schema_id: str
    key: str
    current_value: str
    target_value: str

    @property
    def requires_update(self) -> bool:
        """Return whether this setting needs to be changed."""

        return self.current_value != self.target_value

@dataclass(frozen=True)
class ManagedSetting:
    """A GSettings key managed by Cinnameleon."""

    label: str
    schema_id: str
    key: str

MANAGED_SETTINGS = (
    ManagedSetting(
        label="GTK theme",
        schema_id=INTERFACE_SCHEMA,
        key="gtk-theme",
    ),
    ManagedSetting(
        label="Window borders",
        schema_id=WINDOW_MANAGER_SCHEMA,
        key="theme",
    ),
    ManagedSetting(
        label="Icon theme",
        schema_id=INTERFACE_SCHEMA,
        key="icon-theme",
    ),
    ManagedSetting(
        label="Cursor theme",
        schema_id=INTERFACE_SCHEMA,
        key="cursor-theme",
    ),
    ManagedSetting(
        label="Interface font",
        schema_id=INTERFACE_SCHEMA,
        key="font-name",
    ),
    ManagedSetting(
        label="Document font",
        schema_id=GNOME_INTERFACE_SCHEMA,
        key="document-font-name",
    ),
    ManagedSetting(
        label="Monospace font",
        schema_id=GNOME_INTERFACE_SCHEMA,
        key="monospace-font-name",
    ),
    ManagedSetting(
        label="Window title font",
        schema_id=WINDOW_MANAGER_SCHEMA,
        key="titlebar-font",
    ),
    ManagedSetting(
        label="Wallpaper",
        schema_id=BACKGROUND_SCHEMA,
        key="picture-uri",
    ),
    # Deliberately last because it reloads the Cinnamon shell.
    ManagedSetting(
        label="Cinnamon theme",
        schema_id=CINNAMON_THEME_SCHEMA,
        key="name",
    ),
)

def _wallpaper_uri(path: Path) -> str:
    """Convert a local wallpaper path into a file URI."""

    return Gio.File.new_for_path(str(path.resolve())).get_uri()


ResourceValidator = Callable[[str], bool]


def build_setting_targets(
    profile: EffectiveProfile,
    *,
    include_cinnamon_theme: bool = False,
) -> tuple[SettingTarget, ...]:
    """Map an effective profile to valid GSettings targets."""

    appearance = profile.appearance
    fonts = appearance.fonts
    targets: list[SettingTarget] = []

    def add(
        label: str,
        schema_id: str,
        key: str,
        value: str | None,
    ) -> None:
        if value is None:
            return

        targets.append(
            SettingTarget(
                label=label,
                schema_id=schema_id,
                key=key,
                value=value,
            )
        )

    def add_resource(
        label: str,
        schema_id: str,
        key: str,
        value: str | None,
        validator: ResourceValidator,
    ) -> None:
        """
        Add a resource only when it exists.

        Invalid or missing resources are deliberately skipped so
        the current system value is preserved.
        """

        if value is None:
            return

        if not validator(value):
            return

        add(
            label,
            schema_id,
            key,
            value,
        )

    add_resource(
        "GTK theme",
        INTERFACE_SCHEMA,
        "gtk-theme",
        appearance.gtk_theme,
        gtk_theme_exists,
    )

    add_resource(
        "Window borders",
        WINDOW_MANAGER_SCHEMA,
        "theme",
        appearance.window_borders,
        window_border_theme_exists,
    )

    add_resource(
        "Icon theme",
        INTERFACE_SCHEMA,
        "icon-theme",
        appearance.icon_theme,
        icon_theme_exists,
    )

    add_resource(
        "Cursor theme",
        INTERFACE_SCHEMA,
        "cursor-theme",
        appearance.cursor_theme,
        cursor_theme_exists,
    )

    add_resource(
        "Interface font",
        INTERFACE_SCHEMA,
        "font-name",
        fonts.interface,
        font_exists,
    )

    add_resource(
        "Document font",
        GNOME_INTERFACE_SCHEMA,
        "document-font-name",
        fonts.document,
        font_exists,
    )

    add_resource(
        "Monospace font",
        GNOME_INTERFACE_SCHEMA,
        "monospace-font-name",
        fonts.monospace,
        font_exists,
    )

    add_resource(
        "Window title font",
        WINDOW_MANAGER_SCHEMA,
        "titlebar-font",
        fonts.window_title,
        font_exists,
    )

    # Only apply the wallpaper when the file still exists.
    # Otherwise keep the current system wallpaper.
    if profile.wallpaper.is_file():
        add(
            "Wallpaper",
            BACKGROUND_SCHEMA,
            "picture-uri",
            _wallpaper_uri(profile.wallpaper),
        )

    if include_cinnamon_theme:
        add_resource(
            "Cinnamon theme",
            CINNAMON_THEME_SCHEMA,
            "name",
            appearance.cinnamon_theme,
            cinnamon_theme_exists,
        )

    return tuple(targets)


class SettingsBackend:
    """Read and write Cinnamon appearance settings."""

    def __init__(self) -> None:
        self._settings: dict[str, Gio.Settings] = {}
        self._delayed_schemas: set[str] = set()

    def _schema(self, schema_id: str) -> Gio.SettingsSchema:
        """Find a required GSettings schema."""

        source = Gio.SettingsSchemaSource.get_default()

        if source is None:
            raise SettingsBackendError(
                "The default GSettings schema source is unavailable."
            )

        schema = source.lookup(schema_id, True)

        if schema is None:
            raise SettingsBackendError(
                f"GSettings schema was not found: {schema_id}"
            )

        return schema

    def _settings_for(self, schema_id: str) -> Gio.Settings:
        """Return a cached Gio.Settings object."""

        existing = self._settings.get(schema_id)

        if existing is not None:
            return existing

        schema = self._schema(schema_id)
        settings = Gio.Settings.new_full(schema, None, None)
        self._settings[schema_id] = settings

        return settings

    def _validate_key(
        self,
        schema_id: str,
        key: str,
    ) -> None:
        """Confirm that a schema contains the requested key."""

        schema = self._schema(schema_id)

        if not schema.has_key(key):
            raise SettingsBackendError(
                f"GSettings key was not found: {schema_id}.{key}"
            )

    def read_string(
        self,
        schema_id: str,
        key: str,
    ) -> str:
        """Read a string value from GSettings."""

        self._validate_key(schema_id, key)
        settings = self._settings_for(schema_id)

        return settings.get_string(key)

    def plan_profile(
        self,
        profile: EffectiveProfile,
        *,
        include_cinnamon_theme: bool = False,
    ) -> tuple[SettingChange, ...]:
        """Compare an effective profile with the current system."""

        changes: list[SettingChange] = []

        for target in build_setting_targets(
            profile,
            include_cinnamon_theme=include_cinnamon_theme,
        ):
            current_value = self.read_string(
                target.schema_id,
                target.key,
            )

            changes.append(
                SettingChange(
                    label=target.label,
                    schema_id=target.schema_id,
                    key=target.key,
                    current_value=current_value,
                    target_value=target.value,
                )
            )

        return tuple(changes)
    
    def capture_snapshot(self) -> SettingsSnapshot:
        """Capture all settings managed by Cinnameleon."""

        entries = tuple(
            SnapshotEntry(
                label=setting.label,
                schema_id=setting.schema_id,
                key=setting.key,
                value=self.read_string(
                    setting.schema_id,
                    setting.key,
                ),
            )
            for setting in MANAGED_SETTINGS
        )

        return SettingsSnapshot.create(entries)

    def plan_snapshot_restore(
        self,
        snapshot: SettingsSnapshot,
        *,
        include_cinnamon_theme: bool = False,
    ) -> tuple[SettingChange, ...]:
        """Compare a stored snapshot with the current system."""

        managed_by_key = {
            (setting.schema_id, setting.key): setting
            for setting in MANAGED_SETTINGS
        }

        snapshot_values: dict[tuple[str, str], str] = {}

        for entry in snapshot.settings:
            entry_key = (entry.schema_id, entry.key)

            if entry_key not in managed_by_key:
                raise SettingsBackendError(
                    "Snapshot contains an unmanaged setting: "
                    f"{entry.schema_id}.{entry.key}"
                )

            snapshot_values[entry_key] = entry.value

        missing_settings = [
            setting
            for setting in MANAGED_SETTINGS
            if (
                setting.schema_id,
                setting.key,
            ) not in snapshot_values
        ]

        if missing_settings:
            missing = missing_settings[0]

            raise SettingsBackendError(
                "Snapshot is missing a managed setting: "
                f"{missing.schema_id}.{missing.key}"
            )

        changes: list[SettingChange] = []

        for setting in MANAGED_SETTINGS:
            if (
                setting.schema_id == CINNAMON_THEME_SCHEMA
                and not include_cinnamon_theme
            ):
                continue

            target_value = snapshot_values[
                (setting.schema_id, setting.key)
            ]

            current_value = self.read_string(
                setting.schema_id,
                setting.key,
            )

            changes.append(
                SettingChange(
                    label=setting.label,
                    schema_id=setting.schema_id,
                    key=setting.key,
                    current_value=current_value,
                    target_value=target_value,
                )
            )

        return tuple(changes)

    def _ensure_delayed(
        self,
        schema_id: str,
        settings: Gio.Settings,
    ) -> None:
        """Place a settings object into delay-apply mode once."""

        if schema_id in self._delayed_schemas:
            return

        settings.delay()
        self._delayed_schemas.add(schema_id)

    def _apply_group(
        self,
        schema_id: str,
        changes: Sequence[SettingChange],
        *,
        use_current_values: bool = False,
    ) -> None:
        """Apply one group of keys belonging to the same schema."""

        settings = self._settings_for(schema_id)
        self._ensure_delayed(schema_id, settings)

        for change in changes:
            value = (
                change.current_value
                if use_current_values
                else change.target_value
            )

            if not settings.set_string(change.key, value):
                settings.revert()

                raise SettingsBackendError(
                    "GSettings rejected the value for "
                    f"{change.schema_id}.{change.key}: {value}"
                )

        settings.apply()

    @staticmethod
    def _group_changes(
        changes: Sequence[SettingChange],
    ) -> tuple[tuple[str, tuple[SettingChange, ...]], ...]:
        """Group changes by schema while preserving their order."""

        grouped: dict[str, list[SettingChange]] = defaultdict(list)
        schema_order: list[str] = []

        for change in changes:
            if change.schema_id not in grouped:
                schema_order.append(change.schema_id)

            grouped[change.schema_id].append(change)

        return tuple(
            (
                schema_id,
                tuple(grouped[schema_id]),
            )
            for schema_id in schema_order
        )

    def _rollback(
        self,
        applied_changes: Sequence[SettingChange],
    ) -> None:
        """Best-effort restoration of previously applied values."""

        groups = self._group_changes(applied_changes)

        for schema_id, changes in reversed(groups):
            try:
                self._apply_group(
                    schema_id,
                    changes,
                    use_current_values=True,
                )
            except SettingsBackendError:
                # Preserve the original error. Rollback is best effort.
                continue

        Gio.Settings.sync()

    def apply_changes(
        self,
        planned_changes: Sequence[SettingChange],
    ) -> tuple[SettingChange, ...]:
        """Apply only settings whose values are different."""

        required_changes = tuple(
            change
            for change in planned_changes
            if change.requires_update
        )

        if not required_changes:
            return ()

        applied: list[SettingChange] = []

        try:
            for schema_id, changes in self._group_changes(
                required_changes
            ):
                self._apply_group(schema_id, changes)
                applied.extend(changes)

            # The CLI exits immediately, so make pending writes durable.
            Gio.Settings.sync()

        except SettingsBackendError:
            self._rollback(applied)
            raise

        return tuple(applied)