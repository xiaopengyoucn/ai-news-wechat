from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from fetcher import fetch_all, fetch_one, Item


FAKE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>New Model Released</title><link>https://example.com/1</link>
<description>A new model from lab</description>
<pubDate>Wed, 05 Aug 2026 10:00:00 +0000</pubDate></item>
<item><title>Old Article</title><link>https://example.com/2</link>
<description>Very old</description>
<pubDate>Wed, 01 Jan 2020 10:00:00 +0000</pubDate></item>
</channel></rss>"""


def _now_struct():
    return datetime.now(timezone.utc).timetuple()[:6]


def _entries_mock():
    return MagicMock(entries=[
        MagicMock(
            title="New Model Released",
            link="https://example.com/1",
            summary="A new model from lab",
            published_parsed=_now_struct(),
        ),
    ])


def test_fetch_all_returns_items_within_window():
    sources = [{"name": "Test", "url": "https://example.com/feed", "region": "en"}]
    with patch("fetcher.requests.get") as mock_get, \
         patch("feedparser.parse") as mock_parse:
        mock_get.return_value = MagicMock(content=b"<rss/>", raise_for_status=lambda: None)
        mock_parse.return_value = _entries_mock()
        items = fetch_all(sources, since_hours=24, seen=set())
    assert len(items) == 1
    assert items[0].url == "https://example.com/1"
    assert items[0].source == "Test"
    mock_get.assert_called()
    _, kwargs = mock_get.call_args
    assert "timeout" in kwargs
    assert "Mozilla" in kwargs["headers"]["User-Agent"]
    assert "Accept" in kwargs["headers"]


def test_fetch_all_skips_seen_urls():
    sources = [{"name": "Test", "url": "https://example.com/feed", "region": "en"}]
    with patch("fetcher.requests.get") as mock_get, \
         patch("feedparser.parse") as mock_parse:
        mock_get.return_value = MagicMock(content=b"<rss/>", raise_for_status=lambda: None)
        mock_parse.return_value = MagicMock(entries=[
            MagicMock(
                title="A",
                link="https://example.com/1",
                summary="x",
                published_parsed=_now_struct(),
            ),
        ])
        items = fetch_all(sources, since_hours=24, seen={"https://example.com/1"})
    assert items == []


def test_fetch_all_continues_when_one_source_fails():
    sources = [
        {"name": "Good", "url": "https://good.example/feed", "region": "en"},
        {"name": "Bad", "url": "https://bad.example/feed", "region": "en"},
    ]
    def fake_get(url, **kwargs):
        if "bad" in url:
            raise Exception("boom")
        return MagicMock(content=b"<rss/>", raise_for_status=lambda: None)
    def fake_parse(content):
        return MagicMock(entries=[
            MagicMock(
                title="OK",
                link="https://good.example/1",
                summary="ok",
                published_parsed=_now_struct(),
            )
        ])
    with patch("fetcher.requests.get", side_effect=fake_get), \
         patch("feedparser.parse", side_effect=fake_parse):
        items = fetch_all(sources, since_hours=24, seen=set())
    assert len(items) == 1
    assert items[0].source == "Good"


def test_fetch_one_passes_timeout():
    with patch("fetcher.requests.get") as mock_get, \
         patch("feedparser.parse") as mock_parse:
        mock_get.return_value = MagicMock(content=b"<rss/>", raise_for_status=lambda: None)
        mock_parse.return_value = MagicMock(entries=[])
        fetch_one("https://example.com/feed", timeout=7)
    _, kwargs = mock_get.call_args
    assert kwargs["timeout"] == 7