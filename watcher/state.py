"""Remembers listings between runs in a small JSON file (committed back by the workflow)."""
from __future__ import annotations

import json
from pathlib import Path


def load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"listings": {}, "health": {}}


def save(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=1, sort_keys=True, default=str) + "\n")
