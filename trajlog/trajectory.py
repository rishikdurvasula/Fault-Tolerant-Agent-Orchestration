"""JSONL trajectory logger for tool invocations."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List


class TrajectoryLogger:
    """Append-only JSONL logger for trajectory events.

    Each entry is a JSON object written on its own line.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: Dict[str, Any]) -> None:
        entry = dict(entry)
        # Ensure timestamp if not provided
        if "timestamp" not in entry:
            entry["timestamp"] = time.time()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=_json_fallback) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]


def _json_fallback(obj: Any) -> Any:  # pragma: no cover - trivial
    return str(obj)
