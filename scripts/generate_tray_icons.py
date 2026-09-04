#!/usr/bin/env python3

"""Generate optimized Cinnameleon tray icons from the master PNG."""

from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")

from gi.repository import GdkPixbuf


ICON_SIZES = (16, 22, 24, 32)

# Percentage of the tray canvas occupied by the actual logo.
CONTENT_RATIO = 1


def generate_icon(
    source: Path,
    destination: Path,
    size: int,
) -> None:
    source_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
        str(source)
    )

    source_width = source_pixbuf.get_width()
    source_height = source_pixbuf.get_height()

    content_size = max(
        1,
        round(size * CONTENT_RATIO),
    )

    scale = min(
        content_size / source_width,
        content_size / source_height,
    )

    scaled_width = max(
        1,
        round(source_width * scale),
    )

    scaled_height = max(
        1,
        round(source_height * scale),
    )

    scaled = source_pixbuf.scale_simple(
        scaled_width,
        scaled_height,
        GdkPixbuf.InterpType.HYPER,
    )

    if scaled is None:
        raise RuntimeError(
            f"Could not scale icon to {size}px"
        )

    canvas = GdkPixbuf.Pixbuf.new(
        GdkPixbuf.Colorspace.RGB,
        True,
        8,
        size,
        size,
    )

    # Completely transparent.
    canvas.fill(0x00000000)

    x = (size - scaled_width) // 2
    y = (size - scaled_height) // 2

    scaled.copy_area(
        0,
        0,
        scaled_width,
        scaled_height,
        canvas,
        x,
        y,
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    canvas.savev(
        str(destination),
        "png",
        [],
        [],
    )


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: generate_tray_icons.py "
            "<source.png> <icon-theme-directory>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).resolve()
    icon_theme_directory = Path(
        sys.argv[2]
    ).resolve()

    if not source.is_file():
        print(
            f"Source icon does not exist: {source}",
            file=sys.stderr,
        )
        return 1

    for size in ICON_SIZES:
        destination = (
            icon_theme_directory
            / f"{size}x{size}"
            / "status"
            / (
                "io.github.goncalosamp27."
                "cinnameleon-tray-symbolic.png"
            )
        )

        generate_icon(
            source,
            destination,
            size,
        )

        print(
            f"Generated {size}x{size}: "
            f"{destination}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())