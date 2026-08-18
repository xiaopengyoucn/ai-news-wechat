import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests


log = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
_ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8"


@dataclass
class Item:
    url: str
    title: str
    source: str
    snippet: str
    published: datetime | None


def _to_dt(entry) -> datetime | None:
    if getattr(entry, "published_parsed", None):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None
    if getattr(entry, "published", None):
        try:
            dt = parsedate_to_datetime(entry.published)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (TypeError, ValueError):
            return None
    return None


def fetch_one(url: str, timeout: int = 15) -> feedparser.FeedParserDict:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": _ACCEPT,
                    "Accept-Language": "en-US,en;q=0.9,zh;q=0.8",
                },
            )
            resp.raise_for_status()
            return feedparser.parse(resp.content)
        except Exception as exc:
            last_exc = exc
            log.warning("fetch attempt %d failed for %s: %s", attempt + 1, url, exc)
            time.sleep(0.5 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def fetch_all(sources: list[dict], since_hours: int, seen: set[str], timeout: int = 15) -> list[Item]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    items: list[Item] = []
    for src in sources:
        try:
            feed = fetch_one(src["url"], timeout)
        except Exception as exc:
            log.warning("source %s fetch failed: %s", src["name"], exc)
            continue
        entries = getattr(feed, "entries", None)
        if not entries:
            log.warning("source %s returned no entries", src["name"])
            continue
        for entry in entries:
            link = (getattr(entry, "link", "") or "").strip()
            if not link or link in seen:
                continue
            published = _to_dt(entry)
            if published is not None and published < cutoff:
                continue
            items.append(
                Item(
                    url=link,
                    title=(getattr(entry, "title", "") or "").strip(),
                    source=src["name"],
                    snippet=(getattr(entry, "summary", "") or getattr(entry, "description", "") or "").strip(),
                    published=published,
                )
            )
        time.sleep(0.2)
    return items
