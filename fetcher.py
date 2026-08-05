import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests


log = logging.getLogger(__name__)

_USER_AGENT = "ai-news-wechat/0.1"


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


def fetch_one(url: str, timeout: int = 15):
    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": _USER_AGENT},
    )
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def fetch_all(sources: list[dict], since_hours: int, seen: set[str], timeout: int = 15) -> list[Item]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    items: list[Item] = []
    for src in sources:
        try:
            feed = fetch_one(src["url"], timeout)
        except Exception as exc:
            log.warning("source %s fetch failed: %s", src["name"], exc)
            continue
        if getattr(feed, "entries", None) is None:
            log.warning("source %s returned no entries", src["name"])
            continue
        if getattr(feed, "bozo", False) and not feed.entries:
            log.warning("source %s parse error: %s", src["name"], feed.get("bozo_exception"))
            continue
        for entry in feed.entries:
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
    return items
