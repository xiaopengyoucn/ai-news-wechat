import json
import os
from datetime import datetime, timedelta, timezone


class StateStore:
    def __init__(self, path: str = "state.json"):
        self.path = path
        self._data: dict = {"urls": {}, "last_pushes": []}
        if os.path.exists(path):
            with open(path) as f:
                try:
                    self._data = json.load(f)
                    if "urls" not in self._data or not isinstance(self._data["urls"], dict):
                        self._data["urls"] = {}
                    if "last_pushes" not in self._data or not isinstance(self._data["last_pushes"], list):
                        self._data["last_pushes"] = []
                except json.JSONDecodeError:
                    self._data = {"urls": {}, "last_pushes": []}

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
        cutoff_window = datetime.now(timezone.utc) - timedelta(hours=36)
        self._data["last_pushes"] = [
            p for p in self._data["last_pushes"]
            if _parse_iso(p.get("ts")) >= cutoff_window
        ]

    def was_pushed_today(self, mode: str) -> bool:
        today = datetime.now().astimezone().date().isoformat()
        for p in self._data.get("last_pushes", []):
            if p.get("mode") != mode:
                continue
            ts = p.get("ts", "")
            if not ts:
                continue
            try:
                push_dt = datetime.fromisoformat(ts)
                if push_dt.astimezone().date().isoformat() == today:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    def record_push(self, mode: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._data["last_pushes"].append({"mode": mode, "ts": now})


def _parse_iso(ts: str | None):
    if not ts:
        from datetime import datetime as _dt
        return _dt.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        from datetime import datetime as _dt
        return _dt.min.replace(tzinfo=timezone.utc)
