"""Command-line interface for Cinnameleon."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from cinnameleon import __version__
from cinnameleon.config import (
    load_configuration,
    resolve_config_path,
)
from cinnameleon.inspector import print_inspection
from cinnameleon.models import (
    ConfigIssue,
    Configuration,
    IssueLevel,
    Mode,
)
from cinnameleon.resolver import (
    ProfileNotFoundError,
    resolve_profile,
)
from cinnameleon.settings_backend import (
    SettingChange,
    SettingsBackend,
    SettingsBackendError,
)
from cinnameleon.validator import (
    validate_configuration_resources,
)
from cinnameleon.snapshot import (
    SnapshotError,
    SnapshotStore,
)
from cinnameleon.watcher import WallpaperWatcher

from cinnameleon.application import (
    CinnameleonApplication,
)
from cinnameleon.state import StateError, StateStore

from cinnameleon.resources import ResourceCatalog

def _handle_inspect(_: argparse.Namespace) -> int:
    """Handle the inspect subcommand."""

    print_inspection()
    return 0

def _print_resource_group(
    title: str,
    values: Sequence[str],
) -> None:
    """Print one discovered resource group."""

    print()
    print(f"{title} ({len(values)})")
    print("-" * 32)

    if not values:
        print("(none found)")
        return

    for value in values:
        print(f"• {value}")


def _handle_resources(
    arguments: argparse.Namespace,
) -> int:
    """List appearance resources available on the system."""

    catalog = ResourceCatalog.discover(
        refresh=arguments.refresh
    )

    print("Cinnameleon resources")
    print("=" * 32)

    _print_resource_group(
        "GTK themes",
        catalog.gtk_themes,
    )

    _print_resource_group(
        "Cinnamon themes",
        catalog.cinnamon_themes,
    )

    _print_resource_group(
        "Window borders",
        catalog.window_border_themes,
    )

    _print_resource_group(
        "Icon themes",
        catalog.icon_themes,
    )

    _print_resource_group(
        "Cursor themes",
        catalog.cursor_themes,
    )

    _print_resource_group(
        "Font families",
        catalog.font_families,
    )

    return 0

def _print_issues(
    issues: Sequence[ConfigIssue],
) -> None:
    """Print configuration issues."""

    if not issues:
        return

    print()
    print("Issues")
    print("-" * 32)

    for issue in issues:
        marker = (
            "✗"
            if issue.level is IssueLevel.ERROR
            else "!"
        )

        print(
            f"{marker} [{issue.level.value}] "
            f"{issue.location}: {issue.message}"
        )


def _has_errors(
    issues: Sequence[ConfigIssue],
) -> bool:
    """Return whether an issue sequence contains an error."""

    return any(
        issue.level is IssueLevel.ERROR
        for issue in issues
    )


def _load_validated_configuration(
    config_path: Path,
) -> tuple[
    Configuration | None,
    tuple[ConfigIssue, ...],
]:
    """Load configuration and validate installed resources."""

    result = load_configuration(config_path)
    issues = list(result.issues)

    if result.config is not None:
        issues.extend(
            validate_configuration_resources(
                result.config
            )
        )

    if result.config is None or _has_errors(issues):
        return None, tuple(issues)

    return result.config, tuple(issues)


def _handle_check(arguments: argparse.Namespace) -> int:
    """Load and validate the YAML configuration."""

    config_path = resolve_config_path(arguments.config)
    result = load_configuration(config_path)

    issues = list(result.issues)

    if result.config is not None:
        issues.extend(
            validate_configuration_resources(
                result.config
            )
        )

    has_errors = _has_errors(issues)

    print("Cinnameleon configuration check")
    print("=" * 32)
    print(f"Configuration : {config_path}")
    print(
        "Status        : "
        f"{'Invalid' if has_errors else 'Valid'}"
    )

    if result.config is not None:
        print(f"Profiles      : {len(result.config.profiles)}")
        print(
            "Wallpaper dir : "
            f"{result.config.wallpaper_directory}"
        )

        print()

        for profile in result.config.profiles:
            print(f"✓ {profile.id}")
            print(f"  Name      : {profile.name}")
            print(f"  Wallpaper : {profile.wallpaper}")

    _print_issues(issues)

    return 1 if has_errors else 0


def _display_value(value: str | None) -> str:
    """Format an optional resolved appearance value."""

    if value is None:
        return "(keep current system value)"

    return value


def _handle_resolve(arguments: argparse.Namespace) -> int:
    """Resolve a profile for one dark/light mode."""

    config_path = resolve_config_path(arguments.config)
    result = load_configuration(config_path)

    if result.config is None:
        print("Cannot resolve profile: configuration is invalid.")
        _print_issues(result.issues)
        return 1

    try:
        profile = resolve_profile(
            configuration=result.config,
            profile_id=arguments.profile,
            mode=Mode(arguments.mode),
        )
    except ProfileNotFoundError as error:
        print(f"Error: {error}")
        return 1

    appearance = profile.appearance
    fonts = appearance.fonts

    rows = (
        ("Profile", profile.id),
        ("Name", profile.name),
        ("Mode", profile.mode.value),
        ("Wallpaper", str(profile.wallpaper)),
        ("GTK theme", _display_value(appearance.gtk_theme)),
        (
            "Cinnamon theme",
            _display_value(appearance.cinnamon_theme),
        ),
        (
            "Window borders",
            _display_value(appearance.window_borders),
        ),
        ("Icon theme", _display_value(appearance.icon_theme)),
        (
            "Cursor theme",
            _display_value(appearance.cursor_theme),
        ),
        (
            "Interface font",
            _display_value(fonts.interface),
        ),
        (
            "Document font",
            _display_value(fonts.document),
        ),
        (
            "Monospace font",
            _display_value(fonts.monospace),
        ),
        (
            "Window title",
            _display_value(fonts.window_title),
        ),
    )

    label_width = max(len(label) for label, _ in rows)

    print("Resolved profile")
    print("=" * 32)

    for label, value in rows:
        print(f"{label:<{label_width}} : {value}")

    return 0


def _print_change_plan(
    changes: Sequence[SettingChange],
) -> None:
    """Print current and target values for an apply operation."""

    print()
    print("Changes")
    print("-" * 32)

    for change in changes:
        if change.requires_update:
            print(f"→ {change.label}")
            print(f"  Current : {change.current_value}")
            print(f"  Target  : {change.target_value}")
        else:
            print(
                f"= {change.label}: "
                f"{change.current_value}"
            )


def _handle_apply(arguments: argparse.Namespace) -> int:
    """Resolve and apply one appearance profile."""

    config_path = resolve_config_path(arguments.config)
    configuration, issues = _load_validated_configuration(
        config_path
    )

    if configuration is None:
        print("Cannot apply profile: configuration is invalid.")
        _print_issues(issues)
        return 1

    try:
        profile = resolve_profile(
            configuration=configuration,
            profile_id=arguments.profile,
            mode=Mode(arguments.mode),
        )
    except ProfileNotFoundError as error:
        print(f"Error: {error}")
        return 1

    backend = SettingsBackend()

    try:
        changes = backend.plan_profile(
            profile,
            include_cinnamon_theme=(
                arguments.include_cinnamon_theme
            ),
        )
    except SettingsBackendError as error:
        print(f"Failed to apply profile: {error}")
        print("Restore the previous state with:")
        print("  cinnameleon restore")
        return 1
    
    print("Cinnameleon apply")
    print("=" * 32)
    print(f"Profile       : {profile.id}")
    print(f"Name          : {profile.name}")
    print(f"Mode          : {profile.mode.value}")
    print(f"Configuration : {config_path}")

    _print_change_plan(changes)

    if (
        profile.appearance.cinnamon_theme is not None
        and not arguments.include_cinnamon_theme
    ):
        print()
        print(
            "! Cinnamon theme was skipped for session safety."
        )
        print(
            "  Use --include-cinnamon-theme only for "
            "explicit testing."
        )

    required_count = sum(
        change.requires_update
        for change in changes
    )

    print()

    if arguments.dry_run:
        print(
            "Dry run complete: "
            f"{required_count} setting(s) would change."
        )
        return 0

    if required_count == 0:
        print("No changes are required.")
        return 0

    store = SnapshotStore()

    try:
        safety_snapshot = backend.capture_snapshot()
        snapshot_path = store.save(safety_snapshot)
    except (SettingsBackendError, SnapshotError) as error:
        print(
            "Profile was not applied because the safety "
            f"snapshot failed: {error}"
        )
        return 1

    print(f"Safety snapshot: {snapshot_path}")

    try:
        applied = backend.apply_changes(changes)
    except SettingsBackendError as error:
        print(f"Failed to apply profile: {error}")
        return 1

    print(
        f"Applied {len(applied)} setting change(s) successfully."
    )

    return 0

def _handle_snapshot(arguments: argparse.Namespace) -> int:
    """Save the current desktop appearance state."""

    backend = SettingsBackend()
    store = SnapshotStore()

    try:
        snapshot = backend.capture_snapshot()
        snapshot_path = store.save(
            snapshot,
            arguments.output,
        )
    except (SettingsBackendError, SnapshotError) as error:
        print(f"Could not create snapshot: {error}")
        return 1

    print("Cinnameleon snapshot")
    print("=" * 32)
    print(f"Created : {snapshot.created_at}")
    print(f"Settings: {len(snapshot.settings)}")
    print(f"Saved to: {snapshot_path}")

    return 0

def _handle_restore(arguments: argparse.Namespace) -> int:
    """Restore appearance settings from a saved snapshot."""

    backend = SettingsBackend()
    store = SnapshotStore()

    try:
        snapshot = store.load(arguments.snapshot)

        changes = backend.plan_snapshot_restore(
            snapshot,
            include_cinnamon_theme=(
                arguments.include_cinnamon_theme
            ),
        )
    except (SettingsBackendError, SnapshotError) as error:
        print(f"Could not prepare snapshot restore: {error}")
        return 1

    print("Cinnameleon restore")
    print("=" * 32)
    print(f"Snapshot created: {snapshot.created_at}")

    _print_change_plan(changes)

    if not arguments.include_cinnamon_theme:
        print()
        print(
            "! Cinnamon theme was skipped for session safety."
        )
        print(
            "  Use --include-cinnamon-theme to restore it."
        )

    required_count = sum(
        change.requires_update
        for change in changes
    )

    print()

    if arguments.dry_run:
        print(
            "Dry run complete: "
            f"{required_count} setting(s) would change."
        )
        return 0

    if required_count == 0:
        print("No changes are required.")
        return 0

    try:
        applied = backend.apply_changes(changes)
    except SettingsBackendError as error:
        print(f"Failed to restore snapshot: {error}")
        return 1

    print(
        f"Restored {len(applied)} setting change(s) successfully."
    )

    return 0

def _handle_watch(arguments: argparse.Namespace) -> int:
    """Watch wallpaper changes and synchronize profiles."""

    config_path = resolve_config_path(arguments.config)

    configuration, issues = _load_validated_configuration(
        config_path
    )

    if configuration is None:
        print(
            "Cannot start watcher: "
            "configuration is invalid."
        )
        _print_issues(issues)
        return 1

    watcher = WallpaperWatcher(
        configuration=configuration,
        mode=Mode(arguments.mode),
    )

    print("Cinnameleon wallpaper watcher")
    print("=" * 32)
    print(f"Configuration : {config_path}")
    print(f"Profiles      : {len(configuration.profiles)}")
    print(
        "Cinnamon theme: skipped for session safety"
    )
    print("Stop          : Ctrl+C")
    print()

    watcher.start(
        synchronize_initial=not arguments.no_initial_sync
    )

    return 0

def _handle_run(arguments: argparse.Namespace) -> int:
    """Run the resident single-instance application."""

    config_path = resolve_config_path(
        arguments.config
    )

    try:
        saved_state = StateStore().load()

    except StateError as error:
        print(
            "Warning: could not load "
            f"saved state: {error}"
        )

        saved_mode = Mode.DARK

    else:
        saved_mode = saved_state.mode

    mode = (
        Mode(arguments.mode)
        if arguments.mode is not None
        else saved_mode
    )

    application = CinnameleonApplication(
        config_path=config_path,
        mode=mode,
        synchronize_initial=(
            not arguments.no_initial_sync
        ),
        show_window=arguments.show_window,
        verbose=arguments.verbose,
    )

    print(
        "Cinnameleon resident application"
    )

    print("=" * 32)

    print(
        f"Configuration : {config_path}"
    )

    print(
        f"Mode          : {mode.value}"
    )

    print(
        "Stop          : Ctrl+C"
    )

    print()

    return application.run(
        ["cinnameleon"]
    )

def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="cinnameleon",
        description=(
            "Manage complete appearance profiles "
            "for Linux Mint Cinnamon."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subcommands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    inspect_parser = subcommands.add_parser(
        "inspect",
        help="Show the current Cinnamon appearance settings.",
    )
    inspect_parser.set_defaults(handler=_handle_inspect)

    resources_parser = subcommands.add_parser(
        "resources",
        help=(
            "List themes, icons, cursors and fonts "
            "available on this system."
        ),
    )

    resources_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh the resource discovery cache.",
    )

    resources_parser.set_defaults(
        handler=_handle_resources
    )

    check_parser = subcommands.add_parser(
        "check",
        help="Validate the Cinnameleon YAML configuration.",
    )
    check_parser.add_argument(
        "--config",
        type=Path,
        help=(
            "Configuration file path. Defaults to "
            "~/.config/cinnameleon/config.yaml."
        ),
    )
    check_parser.set_defaults(handler=_handle_check)

    resolve_parser = subcommands.add_parser(
        "resolve",
        help="Resolve a profile using its defaults and mode.",
    )
    resolve_parser.add_argument(
        "profile",
        help="ID of the profile to resolve.",
    )
    resolve_parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in Mode),
        default=Mode.DARK.value,
        help="Appearance mode. Defaults to dark.",
    )
    resolve_parser.add_argument(
        "--config",
        type=Path,
        help=(
            "Configuration file path. Defaults to "
            "~/.config/cinnameleon/config.yaml."
        ),
    )
    resolve_parser.set_defaults(handler=_handle_resolve)

    apply_parser = subcommands.add_parser(
        "apply",
        help="Apply a profile to the current Cinnamon session.",
    )
    apply_parser.add_argument(
        "profile",
        help="ID of the profile to apply.",
    )
    apply_parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in Mode),
        default=Mode.DARK.value,
        help="Appearance mode. Defaults to dark.",
    )
    apply_parser.add_argument(
        "--config",
        type=Path,
        help=(
            "Configuration file path. Defaults to "
            "~/.config/cinnameleon/config.yaml."
        ),
    )
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without modifying the system.",
    )
    apply_parser.add_argument(
        "--include-cinnamon-theme",
        action="store_true",
        help=(
            "Also reload the Cinnamon shell theme. "
            "This can destabilize the current session."
        ),
    )

    apply_parser.set_defaults(handler=_handle_apply)

    snapshot_parser = subcommands.add_parser(
        "snapshot",
        help="Save the current desktop appearance state.",
    )
    snapshot_parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Optional output path. Defaults to the latest "
            "snapshot in the XDG state directory."
        ),
    )
    snapshot_parser.set_defaults(handler=_handle_snapshot)

    restore_parser = subcommands.add_parser(
        "restore",
        help="Restore the most recent appearance snapshot.",
    )
    restore_parser.add_argument(
        "--snapshot",
        type=Path,
        help=(
            "Snapshot file to restore. Defaults to the "
            "most recent safety snapshot."
        ),
    )
    restore_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the restoration plan without changing settings.",
    )
    restore_parser.add_argument(
        "--include-cinnamon-theme",
        action="store_true",
        help=(
            "Also restore the Cinnamon shell theme. "
            "This may reload the current Cinnamon session."
        ),
    )

    restore_parser.set_defaults(handler=_handle_restore)

    watch_parser = subcommands.add_parser(
        "watch",
        help=(
            "Watch wallpaper changes and automatically "
            "synchronize appearance profiles."
        ),
    )

    watch_parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in Mode),
        default=Mode.DARK.value,
        help="Appearance mode. Defaults to dark.",
    )

    watch_parser.add_argument(
        "--config",
        type=Path,
        help=(
            "Configuration file path. Defaults to "
            "~/.config/cinnameleon/config.yaml."
        ),
    )

    watch_parser.add_argument(
        "--no-initial-sync",
        action="store_true",
        help=(
            "Wait for the next wallpaper change instead "
            "of synchronizing immediately."
        ),
    )

    watch_parser.set_defaults(handler=_handle_watch)

    run_parser = subcommands.add_parser(
        "run",
        help=(
            "Run the resident single-instance "
            "Cinnameleon application."
        ),
    )

    run_parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in Mode),
        default=None,
        help=(
            "Override the saved appearance mode for this startup. "
            "Defaults to the previously selected mode."
        ),
    )

    run_parser.add_argument(
        "--config",
        type=Path,
        help=(
            "Configuration file path. Defaults to "
            "~/.config/cinnameleon/config.yaml."
        ),
    )

    run_parser.add_argument(
        "--no-initial-sync",
        action="store_true",
        help=(
            "Do not synchronize the current wallpaper "
            "when the application starts."
        ),
    )

    run_parser.add_argument(
        "--show-window",
        action="store_true",
        help=(
            "Open the graphical profile editor. "
            "If Cinnameleon is already running, "
            "the request is forwarded to it."
        ),
    )

    run_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )

    run_parser.set_defaults(handler=_handle_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Cinnameleon command-line application."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    handler = getattr(arguments, "handler", None)

    if handler is None:
        parser.print_help()
        return 2

    return handler(arguments)