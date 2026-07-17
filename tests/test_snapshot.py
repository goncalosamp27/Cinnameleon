"""Tests for persistent Cinnameleon settings snapshots."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cinnameleon.snapshot import (
    SettingsSnapshot,
    SnapshotEntry,
    SnapshotError,
    SnapshotStore,
)


class SnapshotStoreTests(unittest.TestCase):
    """Verify snapshot serialization and validation."""

    def test_snapshot_round_trip(self) -> None:
        snapshot = SettingsSnapshot.create(
            (
                SnapshotEntry(
                    label="GTK theme",
                    schema_id="org.example.interface",
                    key="gtk-theme",
                    value="Example-Dark",
                ),
                SnapshotEntry(
                    label="Wallpaper",
                    schema_id="org.example.background",
                    key="picture-uri",
                    value="file:///tmp/wallpaper.png",
                ),
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            store = SnapshotStore()

            saved_path = store.save(snapshot, path)
            loaded = store.load(path)

            self.assertEqual(saved_path, path.resolve())
            self.assertEqual(loaded, snapshot)

    def test_invalid_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text("{invalid", encoding="utf-8")

            with self.assertRaises(SnapshotError):
                SnapshotStore().load(path)

    def test_duplicate_settings_are_rejected(self) -> None:
        raw_snapshot = {
            "version": 1,
            "created_at": "2026-01-01T00:00:00+00:00",
            "settings": [
                {
                    "label": "GTK theme",
                    "schema_id": "org.example",
                    "key": "theme",
                    "value": "First",
                },
                {
                    "label": "GTK theme",
                    "schema_id": "org.example",
                    "key": "theme",
                    "value": "Second",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(
                json.dumps(raw_snapshot),
                encoding="utf-8",
            )

            with self.assertRaises(SnapshotError):
                SnapshotStore().load(path)


if __name__ == "__main__":
    unittest.main()
