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


def _handle_inspect(_: argparse.Namespace) -> int:
    """Handle the inspect subcommand."""

    print_inspection()
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
        print(f"Cannot inspect system settings: {error}")
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

    try:
        applied = backend.apply_changes(changes)
    except SettingsBackendError as error:
        print(f"Failed to apply profile: {error}")
        return 1

    print(
        f"Applied {len(applied)} setting change(s) successfully."
    )

    return 0


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