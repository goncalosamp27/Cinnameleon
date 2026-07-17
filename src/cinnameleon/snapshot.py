"""Persistent safety snapshots for Cinnameleon appearance settings."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SNAPSHOT_VERSION = 1


class SnapshotError(RuntimeError):
    """Raised when a settings snapshot cannot be read or written."""


@dataclass(frozen=True)
class SnapshotEntry:
    """One saved GSettings string value."""

    label: str
    schema_id: str
    key: str
    value: str


@dataclass(frozen=True)
class SettingsSnapshot:
    """Complete saved state of Cinnameleon-managed settings."""

    version: int
    created_at: str
    settings: tuple[SnapshotEntry, ...]

    @classmethod
    def create(
        cls,
        settings: tuple[SnapshotEntry, ...],
    ) -> SettingsSnapshot:
        """Create a timestamped snapshot."""

        return cls(
            version=SNAPSHOT_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(),
            settings=settings,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the snapshot into JSON-compatible data."""

        return {
            "version": self.version,
            "created_at": self.created_at,
            "settings": [
                {
                    "label": entry.label,
                    "schema_id": entry.schema_id,
                    "key": entry.key,
                    "value": entry.value,
                }
                for entry in self.settings
            ],
        }


def default_snapshot_path() -> Path:
    """Return the default latest-snapshot path."""

    xdg_state_home = os.environ.get("XDG_STATE_HOME")

    if xdg_state_home:
        state_directory = Path(xdg_state_home).expanduser()
    else:
        state_directory = Path.home() / ".local" / "state"

    return (
        state_directory
        / "cinnameleon"
        / "snapshots"
        / "latest.json"
    )


class SnapshotStore:
    """Read and atomically write settings snapshots."""

    def save(
        self,
        snapshot: SettingsSnapshot,
        path: Path | str | None = None,
    ) -> Path:
        """Save a snapshot using an atomic file replacement."""

        target = (
            default_snapshot_path()
            if path is None
            else Path(path).expanduser()
        )

        target = target.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        temporary_path: Path | None = None

        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".snapshot-",
                suffix=".tmp",
                dir=target.parent,
            )
            temporary_path = Path(temporary_name)

            os.chmod(temporary_path, 0o600)

            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
            ) as snapshot_file:
                json.dump(
                    snapshot.to_dict(),
                    snapshot_file,
                    indent=2,
                    ensure_ascii=False,
                )
                snapshot_file.write("\n")
                snapshot_file.flush()
                os.fsync(snapshot_file.fileno())

            os.replace(temporary_path, target)

        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

            raise SnapshotError(
                f"Could not save snapshot: {error}"
            ) from error

        return target

    def load(
        self,
        path: Path | str | None = None,
    ) -> SettingsSnapshot:
        """Load and validate a settings snapshot."""

        source = (
            default_snapshot_path()
            if path is None
            else Path(path).expanduser()
        )

        source = source.resolve()

        if not source.is_file():
            raise SnapshotError(
                f"Snapshot file does not exist: {source}"
            )

        try:
            with source.open("r", encoding="utf-8") as snapshot_file:
                raw_snapshot = json.load(snapshot_file)
        except OSError as error:
            raise SnapshotError(
                f"Could not read snapshot: {error}"
            ) from error
        except json.JSONDecodeError as error:
            raise SnapshotError(
                f"Snapshot contains invalid JSON: {error}"
            ) from error

        if not isinstance(raw_snapshot, dict):
            raise SnapshotError(
                "Snapshot root must be a JSON object."
            )

        version = raw_snapshot.get("version")
        created_at = raw_snapshot.get("created_at")
        raw_settings = raw_snapshot.get("settings")

        if version != SNAPSHOT_VERSION:
            raise SnapshotError(
                f"Unsupported snapshot version: {version}"
            )

        if not isinstance(created_at, str) or not created_at:
            raise SnapshotError(
                "Snapshot created_at value is invalid."
            )

        if not isinstance(raw_settings, list):
            raise SnapshotError(
                "Snapshot settings value must be a list."
            )

        entries: list[SnapshotEntry] = []
        seen_keys: set[tuple[str, str]] = set()

        for index, raw_entry in enumerate(raw_settings):
            if not isinstance(raw_entry, dict):
                raise SnapshotError(
                    f"Snapshot setting {index} must be an object."
                )

            values = {
                field: raw_entry.get(field)
                for field in (
                    "label",
                    "schema_id",
                    "key",
                    "value",
                )
            }

            for field, value in values.items():
                if not isinstance(value, str) or not value:
                    raise SnapshotError(
                        f"Snapshot setting {index}.{field} "
                        "must be a non-empty string."
                    )

            entry_key = (
                values["schema_id"],
                values["key"],
            )

            if entry_key in seen_keys:
                raise SnapshotError(
                    "Snapshot contains a duplicate setting: "
                    f"{entry_key[0]}.{entry_key[1]}"
                )

            seen_keys.add(entry_key)

            entries.append(
                SnapshotEntry(
                    label=values["label"],
                    schema_id=values["schema_id"],
                    key=values["key"],
                    value=values["value"],
                )
            )

        return SettingsSnapshot(
            version=version,
            created_at=created_at,
            settings=tuple(entries),
        )