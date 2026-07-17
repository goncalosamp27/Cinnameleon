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
from cinnameleon.models import IssueLevel

from cinnameleon.validator import (
    validate_configuration_resources,
)


def _handle_inspect(_: argparse.Namespace) -> int:
    """Handle the inspect subcommand."""

    print_inspection()
    return 0


def _handle_check(arguments: argparse.Namespace) -> int:
    """Load and validate the YAML configuration."""

    config_path = resolve_config_path(arguments.config)
    result = load_configuration(config_path)

    issues = list(result.issues)

    if result.config is not None:
        resource_issues = validate_configuration_resources(
            result.config
        )
        issues.extend(resource_issues)

    has_errors = any(
        issue.level is IssueLevel.ERROR
        for issue in issues
    )

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

    if issues:
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

    return 1 if has_errors else 0


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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Cinnameleon command-line application."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    return arguments.handler(arguments)