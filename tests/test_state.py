import json
import os
import tempfile
from state import StateStore


def test_state_empty_when_no_file():
    with tempfile.TemporaryDirectory() as d:
        store = StateStore(os.path.join(d, "state.json"))
        assert store.seen_urls() == set()


def test_state_round_trip():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        store = StateStore(path)
        store.add(["https://a.com", "https://b.com"])
        store.save()
        store2 = StateStore(path)
        assert store2.seen_urls() == {"https://a.com", "https://b.com"}


def test_state_prune_keeps_only_added_urls_in_window():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    keep_ts = (now - timedelta(days=1)).isoformat()
    old_ts = (now - timedelta(days=30)).isoformat()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        with open(path, "w") as f:
            json.dump(
                {
                    "urls": {
                        "https://keep.com": keep_ts,
                        "https://old.com": old_ts,
                    }
                },
                f,
            )
        store = StateStore(path)
        store.prune_older_than(days=7)
        store.save()
        with open(path) as f:
            data = json.load(f)
        assert "https://keep.com" in data["urls"]
        assert "https://old.com" not in data["urls"]
