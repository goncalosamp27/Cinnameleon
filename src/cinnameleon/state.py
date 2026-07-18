"""Persistent runtime state for Cinnameleon."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cinnameleon.models import Mode


STATE_VERSION = 1


class StateError(RuntimeError):
    """Raised when application state cannot be loaded or saved."""


@dataclass(frozen=True)
class ApplicationState:
    """Persistent Cinnameleon runtime state."""

    mode: Mode = Mode.DARK

    def to_dict(self) -> dict[str, Any]:
        """Convert state into JSON-compatible data."""

        return {
            "version": STATE_VERSION,
            "mode": self.mode.value,
        }


def default_state_path() -> Path:
    """Return the XDG state file path."""

    xdg_state_home = os.environ.get("XDG_STATE_HOME")

    if xdg_state_home:
        state_directory = Path(xdg_state_home).expanduser()
    else:
        state_directory = Path.home() / ".local" / "state"

    return state_directory / "cinnameleon" / "state.json"


class StateStore:
    """Load and atomically save application state."""

    def load(
        self,
        path: Path | str | None = None,
    ) -> ApplicationState:
        """Load state, returning defaults when no file exists."""

        source = (
            default_state_path()
            if path is None
            else Path(path).expanduser()
        )

        source = source.resolve()

        if not source.exists():
            return ApplicationState()

        if not source.is_file():
            raise StateError(
                f"State path is not a file: {source}"
            )

        try:
            with source.open("r", encoding="utf-8") as state_file:
                raw_state = json.load(state_file)
        except OSError as error:
            raise StateError(
                f"Could not read state: {error}"
            ) from error
        except json.JSONDecodeError as error:
            raise StateError(
                f"State contains invalid JSON: {error}"
            ) from error

        if not isinstance(raw_state, dict):
            raise StateError(
                "State root must be a JSON object."
            )

        version = raw_state.get("version")

        if version != STATE_VERSION:
            raise StateError(
                f"Unsupported state version: {version}"
            )

        raw_mode = raw_state.get("mode")

        try:
            mode = Mode(raw_mode)
        except ValueError as error:
            raise StateError(
                f"Invalid saved mode: {raw_mode!r}"
            ) from error

        return ApplicationState(mode=mode)

    def save(
        self,
        state: ApplicationState,
        path: Path | str | None = None,
    ) -> Path:
        """Save state using an atomic file replacement."""

        target = (
            default_state_path()
            if path is None
            else Path(path).expanduser()
        )

        target = target.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        temporary_path: Path | None = None

        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".state-",
                suffix=".tmp",
                dir=target.parent,
            )

            temporary_path = Path(temporary_name)
            os.chmod(temporary_path, 0o600)

            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
            ) as state_file:
                json.dump(
                    state.to_dict(),
                    state_file,
                    indent=2,
                )
                state_file.write("\n")
                state_file.flush()
                os.fsync(state_file.fileno())

            os.replace(temporary_path, target)

        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

            raise StateError(
                f"Could not save state: {error}"
            ) from error

        return target
