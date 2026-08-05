import json
import os
from datetime import datetime, timedelta, timezone


class StateStore:
    def __init__(self, path: str = "state.json"):
        self.path = path
        self._data = {"urls": {}}
        if os.path.exists(path):
            with open(path) as f:
                try:
                    self._data = json.load(f)
                    if "urls" not in self._data or not isinstance(self._data["urls"], dict):
                        self._data["urls"] = {}
                except json.JSONDecodeError:
                    self._data = {"urls": {}}

    def seen_urls(self) -> set[str]:
        return set(self._data["urls"].keys())

    def add(self, urls: list[str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for u in urls:
            self._data["urls"][u] = now

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def prune_older_than(self, days: int = 7) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        kept = {}
        for url, ts in self._data["urls"].items():
            try:
                parsed = datetime.fromisoformat(ts)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed >= cutoff:
                    kept[url] = ts
            except (ValueError, TypeError):
                kept[url] = ts
        self._data["urls"] = kept
