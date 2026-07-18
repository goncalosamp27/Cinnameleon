"""Logging configuration for the resident Cinnameleon application."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "cinnameleon"


def default_log_path() -> Path:
    """Return the log path according to the XDG specification."""

    xdg_state_home = os.environ.get("XDG_STATE_HOME")

    if xdg_state_home:
        state_directory = Path(xdg_state_home).expanduser()
    else:
        state_directory = Path.home() / ".local" / "state"

    return state_directory / "cinnameleon" / "cinnameleon.log"


def configure_logging(
    *,
    console: bool = True,
    verbose: bool = False,
) -> logging.Logger:
    """Configure persistent rotating logs."""

    logger = logging.getLogger(LOGGER_NAME)

    if logger.handlers:
        return logger

    logger.setLevel(
        logging.DEBUG if verbose else logging.INFO
    )
    logger.propagate = False

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)-8s | "
            "%(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_path = default_log_path()
    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.debug("Logging initialized: %s", log_path)

    return logger
