"""Tests for persistent application state."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cinnameleon.models import Mode
from cinnameleon.state import (
    ApplicationState,
    StateError,
    StateStore,
)


class StateStoreTests(unittest.TestCase):
    """Verify application state persistence."""

    def test_missing_file_returns_dark_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"

            state = StateStore().load(path)

            self.assertEqual(state.mode, Mode.DARK)

    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store = StateStore()

            store.save(
                ApplicationState(mode=Mode.LIGHT),
                path,
            )

            loaded = store.load(path)

            self.assertEqual(loaded.mode, Mode.LIGHT)

    def test_invalid_mode_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"

            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mode": "automatic",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(StateError):
                StateStore().load(path)


if __name__ == "__main__":
    unittest.main()
