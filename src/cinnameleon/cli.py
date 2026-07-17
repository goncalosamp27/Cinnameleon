"""Command-line interface for Cinnameleon."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from cinnameleon import __version__
from cinnameleon.inspector import print_inspection


def _handle_inspect(_: argparse.Namespace) -> int:
    """Handle the inspect subcommand."""

    print_inspection()
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Cinnameleon command-line application."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    return arguments.handler(arguments)