# AI 新闻微信聚合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated pipeline that fetches AI news from ~20 RSS sources twice daily, uses DeepSeek to translate and score items, and pushes a curated digest to personal WeChat via PushPlus.

**Architecture:** Modular Python pipeline (sources → fetcher → processor → publisher) orchestrated by `main.py`, deployed via GitHub Actions cron at 00:00 UTC and 12:00 UTC (~08:00 / 20:00 Asia/Shanghai).

**Tech Stack:** Python 3.11, feedparser, requests, openai-sdk (OpenAI-compatible), DeepSeek API, PushPlus HTTP API, pytest, GitHub Actions.

## Global Constraints

- Python 3.11+ required.
- `importance` threshold: `>= 6`. Maximum 15 items per push.
- Time windows: morning digest = last 12 hours, evening digest = last 12 hours.
- Lookback is `since_hours` parameter; `main.py` computes it as 12.
- LLM provider: DeepSeek via OpenAI-compatible base URL `https://api.deepseek.com/v1`, model `deepseek-chat`.
- PushPlus channel: `wechat`. Auth via single token in env var `PUSHPLUS_TOKEN`.
- State persistence via `state.json` uploaded/downloaded as GitHub Actions artifact.
- Single-error tolerance per source: log + skip, never crash the whole pipeline.
- All secrets read from environment variables only. Never hardcode API keys.
- All tests are unit tests with mocked I/O — no real network calls in CI.
- Use environment variable names: `DEEPSEEK_API_KEY`, `PUSHPLUS_TOKEN`, optional `LLM_MODEL`, `PUSHPLUS_TOPIC`.
- Imports use stdlib + the four deps above. No extra libraries.

---

## File Structure

| Path | Responsibility |
|---|---|
| `sources.py` | Static list of RSS source dicts (name, url, region) |
| `state.py` | Read/write `state.json` for URL dedup |
| `fetcher.py` | Fetch RSS, parse, time-window filter, dedup via state |
| `processor.py` | Batch call DeepSeek LLM, parse JSON, filter importance>=6, sort, top 15 |
| `publisher.py` | Render markdown digest, POST to PushPlus |
| `main.py` | CLI entry: `--mode morning|evening`, orchestrate pipeline |
| `requirements.txt` | `feedparser`, `requests`, `openai`, `pytest` |
| `.github/workflows/daily.yml` | Production cron |
| `.github/workflows/ci.yml` | PR/push test runner |
| `tests/test_state.py` | State persistence |
| `tests/test_fetcher.py` | RSS fetch + dedup |
| `tests/test_processor.py` | LLM batch + filter |
| `tests/test_publisher.py` | PushPlus POST + markdown rendering |
| `README.md` | Setup instructions |
| `.gitignore` | Python defaults + state.json |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `.gitignore`, `README.md` placeholder, `tests/__init__.py`

**Interfaces:** None (foundation only)

- [ ] **Step 1: Initialize git and basic project files**

```bash
cd C:\Users\Administrator\AppData\Local\Temp\opencode\ai-news-wechat
git init
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "ai-news-wechat"
version = "0.1.0"
description = "AI news digest to personal WeChat via PushPlus"
requires-python = ">=3.11"
```

- [ ] **Step 3: Write `requirements.txt`**

```
feedparser>=6.0.10
requests>=2.31.0
openai>=1.30.0
pytest>=8.0.0
```

- [ ] **Step 4: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.env
state.json
.pytest_cache/
output/
```

- [ ] **Step 5: Create empty package init `tests/__init__.py`**

```bash
type nul > tests\__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "chore: project scaffold"
```

---

## Task 2: `state.py` with TDD

**Files:**
- Create: `state.py`, `tests/test_state.py`

**Interfaces (consumed by later tasks):**
- `class StateStore`
  - `__init__(self, path: str = "state.json")`
  - `seen_urls(self) -> set[str]`
  - `add(self, urls: list[str]) -> None`
  - `save(self) -> None`
  - `prune_older_than(self, days: int = 7) -> None`

- [ ] **Step 1: Write failing test `tests/test_state.py`**

```python
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
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.json")
        with open(path, "w") as f:
            json.dump(
                {
                    "urls": {
                        "https://keep.com": "2026-08-05T10:00:00+00:00",
                        "https://old.com": "2020-01-01T00:00:00+00:00",
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
```

- [ ] **Step 2: Run tests (expect FAIL)**

Run: `pytest tests/test_state.py -v`
Expected: `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Implement `state.py`**

```python
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
```

- [ ] **Step 4: Run tests (expect PASS)**

Run: `pytest tests/test_state.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat(state): URL dedup persistence with sliding window"
```

---

## Task 3: `sources.py`

**Files:**
- Create: `sources.py`

**Interfaces (consumed by fetcher):**
- `SOURCES: list[dict]` where each dict has keys: `name`, `url`, `region` (en: `en` | `zh`)
- `get_sources() -> list[dict]` returns `SOURCES`

- [ ] **Step 1: Implement `sources.py`**

```python
SOURCES = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "region": "en"},
    {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss.xml", "region": "en"},
    {"name": "Google DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml", "region": "en"},
    {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/", "region": "en"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "region": "en"},
    {"name": "arXiv cs.AI", "url": "https://export.arxiv.org/rss/cs.AI", "region": "en"},
    {"name": "arXiv cs.CL", "url": "https://export.arxiv.org/rss/cs.CL", "region": "en"},
    {"name": "arXiv cs.LG", "url": "https://export.arxiv.org/rss/cs.LG", "region": "en"},
    {"name": "Hacker News (newest)", "url": "https://hnrss.org/newest?q=AI", "region": "en"},
    {"name": "Reddit r/MachineLearning", "url": "https://www.reddit.com/r/MachineLearning/.rss", "region": "en"},
    {"name": "Reddit r/LocalLLaMA", "url": "https://www.reddit.com/r/LocalLLaMA/.rss", "region": "en"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "region": "en"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "region": "en"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "region": "en"},
    {"name": "The Decoder", "url": "https://the-decoder.com/feed/", "region": "en"},
    {"name": "Import AI", "url": "https://importai.substack.com/feed", "region": "en"},
    {"name": "The Batch", "url": "https://www.deeplearning.ai/the-batch/feed/", "region": "en"},
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "region": "zh"},
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "region": "zh"},
    {"name": "36氪 AI频道", "url": "https://36kr.com/feed", "region": "zh"},
]


def get_sources() -> list[dict]:
    return SOURCES
```

- [ ] **Step 2: Quick smoke test (no test framework)**

Run: `python -c "from sources import get_sources; print(len(get_sources()))"`
Expected: `20`

- [ ] **Step 3: Commit**

```bash
git add sources.py
git commit -m "feat(sources): AI RSS source registry (~20 sources)"
```

---

## Task 4: `fetcher.py` with TDD

**Files:**
- Create: `fetcher.py`, `tests/test_fetcher.py`

**Interfaces (consumed by main):**
- `dataclass Item` with `url`, `title`, `source`, `snippet`, `published (datetime | None)`
- `def fetch_all(sources: list[dict], since_hours: int, seen: set[str], timeout: int = 15) -> list[Item]`

- [ ] **Step 1: Write failing test `tests/test_fetcher.py`**

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from fetcher import fetch_all, Item


FAKE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>New Model Released</title><link>https://example.com/1</link>
<description>A new model from lab</description>
<pubDate>Wed, 05 Aug 2026 10:00:00 +0000</pubDate></item>
<item><title>Old Article</title><link>https://example.com/2</link>
<description>Very old</description>
<pubDate>Wed, 01 Jan 2020 10:00:00 +0000</pubDate></item>
</channel></rss>"""


def test_fetch_all_returns_items_within_window():
    sources = [{"name": "Test", "url": "https://example.com/feed", "region": "en"}]
    with patch("feedparser.parse") as mock_parse:
        mock_parse.return_value = MagicMock(entries=[
            MagicMock(
                title="New Model Released",
                link="https://example.com/1",
                summary="A new model from lab",
                published_parsed=(2026, 8, 5, 10, 0, 0, 0, 0, 0),
            ),
        ])
        items = fetch_all(sources, since_hours=24, seen=set())
    assert len(items) == 1
    assert items[0].url == "https://example.com/1"
    assert items[0].source == "Test"


def test_fetch_all_skips_seen_urls():
    sources = [{"name": "Test", "url": "https://example.com/feed", "region": "en"}]
    with patch("feedparser.parse") as mock_parse:
        mock_parse.return_value = MagicMock(entries=[
            MagicMock(
                title="A",
                link="https://example.com/1",
                summary="x",
                published_parsed=(2026, 8, 5, 10, 0, 0, 0, 0, 0),
            ),
        ])
        items = fetch_all(sources, since_hours=24, seen={"https://example.com/1"})
    assert items == []


def test_fetch_all_continues_when_one_source_fails():
    sources = [
        {"name": "Good", "url": "https://good.example/feed", "region": "en"},
        {"name": "Bad", "url": "https://bad.example/feed", "region": "en"},
    ]
    def fake_parse(url):
        if "bad" in url:
            raise Exception("boom")
        m = MagicMock(entries=[
            MagicMock(
                title="OK",
                link="https://good.example/1",
                summary="ok",
                published_parsed=(2026, 8, 5, 10, 0, 0, 0, 0, 0),
            )
        ])
        return m
    with patch("feedparser.parse", side_effect=fake_parse):
        items = fetch_all(sources, since_hours=24, seen=set())
    assert len(items) == 1
    assert items[0].source == "Good"
```

- [ ] **Step 2: Run tests (expect FAIL)**

Run: `pytest tests/test_fetcher.py -v`
Expected: `ModuleNotFoundError: No module named 'fetcher'`

- [ ] **Step 3: Implement `fetcher.py`**

```python
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser


log = logging.getLogger(__name__)


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
    return feedparser.parse(url, agent="ai-news-wechat/0.1")


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
            link = (entry.get("link") or "").strip()
            if not link or link in seen:
                continue
            published = _to_dt(entry)
            if published is not None and published < cutoff:
                continue
            items.append(
                Item(
                    url=link,
                    title=(entry.get("title") or "").strip(),
                    source=src["name"],
                    snippet=(entry.get("summary") or entry.get("description") or "").strip(),
                    published=published,
                )
            )
    return items
```

- [ ] **Step 4: Run tests (expect PASS)**

Run: `pytest tests/test_fetcher.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add fetcher.py tests/test_fetcher.py
git commit -m "feat(fetcher): RSS fetch with time-window filter and dedup"
```

---

## Task 5: `processor.py` with TDD

**Files:**
- Create: `processor.py`, `tests/test_processor.py`

**Interfaces (consumed by main):**
- `dataclass Processed` with `url`, `title_zh`, `summary_zh`, `importance (int)`, `category (str)`, `source`
- `def enrich(items: list[Item], api_key: str, model: str = "deepseek-chat", base_url: str = "https://api.deepseek.com/v1") -> list[Processed]`
- `def fallback_processed(items: list[Item]) -> list[Processed]` for English-only fallback

- [ ] **Step 1: Write failing test `tests/test_processor.py`**

```python
from unittest.mock import patch, MagicMock
from fetcher import Item
from processor import enrich, fallback_processed


def _fake_completion(content_str: str):
    return MagicMock(
        choices=[MagicMock(message=MagicMock(content=content_str))]
    )


def test_enrich_parses_json_and_filters():
    items = [
        Item(url="https://a/1", title="Big breakthrough", source="Test", snippet="x", published=None),
        Item(url="https://a/2", title="Minor update", source="Test", snippet="y", published=None),
    ]
    fake_json = (
        '[{"url":"https://a/1","title_zh":"重大突破","summary_zh":"一句话","importance":9,"category":"研究"},'
        '{"url":"https://a/2","title_zh":"小更新","summary_zh":"另一句","importance":3,"category":"产品"}]'
    )
    with patch("openai.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _fake_completion(fake_json)
        result = enrich(items, api_key="test-key")
    assert len(result) == 1
    assert result[0].url == "https://a/1"
    assert result[0].importance == 9


def test_enrich_sorts_by_importance_desc():
    items = [
        Item(url="https://a/1", title="A", source="S", snippet="", published=None),
        Item(url="https://a/2", title="B", source="S", snippet="", published=None),
    ]
    fake_json = (
        '[{"url":"https://a/1","title_zh":"1","summary_zh":"1","importance":5,"category":"研究"},'
        '{"url":"https://a/2","title_zh":"2","summary_zh":"2","importance":9,"category":"研究"}]'
    )
    with patch("openai.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _fake_completion(fake_json)
        result = enrich(items, api_key="k")
    assert result[0].url == "https://a/2"


def test_enrich_returns_empty_for_empty_items():
    with patch("openai.OpenAI") as MockClient:
        result = enrich([], api_key="k")
    assert result == []
    MockClient.return_value.chat.completions.create.assert_not_called()


def test_enrich_top_n_cap():
    items = [Item(url=f"https://a/{i}", title=f"t{i}", source="S", snippet="", published=None) for i in range(20)]
    fake_json = "[" + ",".join(
        f'{{"url":"https://a/{i}","title_zh":"t{i}","summary_zh":"x","importance":{10 - i // 2},"category":"研"}}'
        for i in range(20)
    ) + "]"
    with patch("openai.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _fake_completion(fake_json)
        result = enrich(items, api_key="k", top_n=5)
    assert len(result) == 5


def test_fallback_returns_processed_zero_importance():
    items = [Item(url="https://a/1", title="T", source="S", snippet="S", published=None)]
    result = fallback_processed(items)
    assert result[0].importance == 0
    assert result[0].title_zh == "T"
```

- [ ] **Step 2: Run tests (expect FAIL)**

Run: `pytest tests/test_processor.py -v`
Expected: `ModuleNotFoundError: No module named 'processor'`

- [ ] **Step 3: Implement `processor.py`**

```python
import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from fetcher import Item


log = logging.getLogger(__name__)


@dataclass
class Processed:
    url: str
    title_zh: str
    summary_zh: str
    importance: int
    category: str
    source: str


_PROMPT = """你是 AI 行业编辑。下面是 {n} 条英文新闻条目，请对每一条：
1. 把 title 翻译为中文（保留专有名词原文）
2. 用一句中文给出摘要（不超过 30 字）
3. 用 0-10 给出重要性（真正改变行业格局的给 9-10，重大发布 7-8，小更新 4-6，无关 0-3）
4. 给出类别：研究/产品/行业/工具

严格返回 JSON 数组，每条形如：
{{"url":"原文url","title_zh":"...","summary_zh":"...","importance":0,"category":"研究"}}

条目：
{entries}
"""


def _build_prompt(items: list[Item]) -> str:
    lines = []
    for i, it in enumerate(items, 1):
        snippet = (it.snippet or "")[:300]
        lines.append(f"{i}. url={it.url}\n   title={it.title}\n   snippet={snippet}")
    return _PROMPT.format(n=len(items), entries="\n".join(lines))


def _parse_json_block(content: str) -> list[dict] | None:
    content = content.strip()
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
    if m:
        content = m.group(1)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return data


def enrich(
    items: list[Item],
    api_key: str,
    model: str = "deepseek-chat",
    base_url: str = "https://api.deepseek.com/v1",
    top_n: int = 15,
    importance_threshold: int = 6,
) -> list[Processed]:
    if not items:
        return []

    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = _build_prompt(items)

    last_err: Exception | None = None
    parsed: list[dict] | None = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            parsed = _parse_json_block(resp.choices[0].message.content or "")
            if parsed is not None:
                break
        except Exception as exc:
            last_err = exc
            log.warning("LLM call attempt %d failed: %s", attempt + 1, exc)
            parsed = None

    if parsed is None:
        log.error("LLM failed after retries: %s", last_err)
        return fallback_processed(items)

    by_url = {it.url: it for it in items}
    processed: list[Processed] = []
    for row in parsed:
        url = row.get("url", "").strip()
        it = by_url.get(url)
        if not it:
            continue
        try:
            importance = int(row.get("importance", 0))
        except (TypeError, ValueError):
            importance = 0
        if importance < importance_threshold:
            continue
        processed.append(
            Processed(
                url=url,
                title_zh=str(row.get("title_zh") or it.title).strip(),
                summary_zh=str(row.get("summary_zh") or "").strip(),
                importance=importance,
                category=str(row.get("category") or "其他"),
                source=it.source,
            )
        )

    processed.sort(key=lambda p: p.importance, reverse=True)
    return processed[:top_n]


def fallback_processed(items: list[Item]) -> list[Processed]:
    return [
        Processed(
            url=it.url,
            title_zh=it.title,
            summary_zh=it.snippet[:80] if it.snippet else "(无摘要)",
            importance=0,
            category="原始",
            source=it.source,
        )
        for it in items
    ]
```

- [ ] **Step 4: Run tests (expect PASS)**

Run: `pytest tests/test_processor.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add processor.py tests/test_processor.py
git commit -m "feat(processor): DeepSeek LLM enrichment with importance filter"
```

---

## Task 6: `publisher.py` with TDD

**Files:**
- Create: `publisher.py`, `tests/test_publisher.py`

**Interfaces (consumed by main):**
- `def render_markdown(title: str, items: list[Processed]) -> str`
- `def publish_pushplus(title: str, content_md: str, token: str, topic: str | None = None, timeout: int = 15) -> int` returns HTTP status code

- [ ] **Step 1: Write failing test `tests/test_publisher.py`**

```python
from unittest.mock import patch, MagicMock

from processor import Processed
from publisher import render_markdown, publish_pushplus


def _items():
    return [
        Processed(url="https://a/1", title_zh="突破", summary_zh="一句话", importance=9, category="研究", source="OpenAI"),
        Processed(url="https://a/2", title_zh="更新", summary_zh="一句话2", importance=7, category="产品", source="Anthropic"),
    ]


def test_render_markdown_contains_title_and_urls():
    md = render_markdown("AI 早报", _items())
    assert "AI 早报" in md
    assert "https://a/1" in md
    assert "https://a/2" in md
    assert "[研究]" in md
    assert "突破" in md


def test_publish_pushplus_posts_to_correct_url():
    with patch("publisher.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        code = publish_pushplus("hi", "body", token="tok")
    assert code == 200
    args, kwargs = mock_post.call_args
    assert args[0] == "https://www.pushplus.plus/send"
    assert kwargs["json"]["title"] == "hi"
    assert kwargs["json"]["content"] == "body"
    assert kwargs["json"]["token"] == "tok"
    assert kwargs["json"]["channel"] == "wechat"


def test_publish_pushplus_includes_topic_when_given():
    with patch("publisher.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        publish_pushplus("hi", "body", token="tok", topic="mygroup")
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["topic"] == "mygroup"
```

- [ ] **Step 2: Run tests (expect FAIL)**

Run: `pytest tests/test_publisher.py -v`
Expected: `ModuleNotFoundError: No module named 'publisher'`

- [ ] **Step 3: Implement `publisher.py`**

```python
import logging

import requests

from processor import Processed


log = logging.getLogger(__name__)

_PUSHPLUS_URL = "https://www.pushplus.plus/send"


def render_markdown(title: str, items: list[Processed]) -> str:
    if not items:
        body = "今日 AI 信源无重要更新。可手动访问 PushPlus 或 GitHub Pages 回看。"
    else:
        by_cat: dict[str, list[Processed]] = {}
        for it in items:
            by_cat.setdefault(it.category, []).append(it)
        lines = [f"# {title}", ""]
        for cat in sorted(by_cat.keys()):
            lines.append(f"## {cat}")
            lines.append("")
            for it in by_cat[cat]:
                lines.append(f"**[{it.importance}] {it.title_zh}**")
                lines.append("")
                lines.append(f"> {it.summary_zh}")
                lines.append("")
                lines.append(f"来源：{it.source}  [阅读原文]({it.url})")
                lines.append("")
        body = "\n".join(lines)
    return body


def publish_pushplus(
    title: str,
    content_md: str,
    token: str,
    topic: str | None = None,
    timeout: int = 15,
) -> int:
    payload = {
        "token": token,
        "title": title,
        "content": content_md,
        "template": "markdown",
        "channel": "wechat",
    }
    if topic:
        payload["topic"] = topic

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.post(_PUSHPLUS_URL, json=payload, timeout=timeout)
            if resp.status_code < 500:
                log.info("pushplus response %s: %s", resp.status_code, resp.text[:200])
                return resp.status_code
            log.warning("pushplus 5xx attempt %d: %s", attempt + 1, resp.status_code)
        except Exception as exc:
            last_err = exc
            log.warning("pushplus attempt %d failed: %s", attempt + 1, exc)
    log.error("pushplus failed after retries: %s", last_err)
    return 0
```

- [ ] **Step 4: Run tests (expect PASS)**

Run: `pytest tests/test_publisher.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add publisher.py tests/test_publisher.py
git commit -m "feat(publisher): PushPlus markdown push with category grouping"
```

---

## Task 7: `main.py` (Orchestration)

**Files:**
- Create: `main.py`

**Interfaces:**
- `python main.py --mode morning|evening`
- Reads `DEEPSEEK_API_KEY`, `PUSHPLUS_TOKEN` from env
- Writes `state.json` and `output/<mode>_YYYYMMDD_HHMMSS.md` artifact

- [ ] **Step 1: Implement `main.py`**

```python
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from fetcher import fetch_all
from sources import get_sources
from state import StateStore
from processor import enrich, fallback_processed
from publisher import render_markdown, publish_pushplus


log = logging.getLogger("ai-news-wechat")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _make_title(mode: str) -> str:
    cn = "早报" if mode == "morning" else "晚报"
    return f"AI {cn} · {datetime.now().strftime('%m-%d')}"


def run(mode: str) -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    token = os.environ.get("PUSHPLUS_TOKEN")
    topic = os.environ.get("PUSHPLUS_TOPIC")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")

    if not api_key:
        log.error("DEEPSEEK_API_KEY not set")
        return 1
    if not token:
        log.error("PUSHPLUS_TOKEN not set")
        return 1

    state = StateStore("state.json")
    state.prune_older_than(days=7)

    since_hours = 12
    log.info("fetching sources (mode=%s, since_hours=%d)", mode, since_hours)
    items = fetch_all(get_sources(), since_hours=since_hours, seen=state.seen_urls())
    log.info("fetched %d items", len(items))

    processed = enrich(items, api_key=api_key, model=model) if items else []
    if not processed and items:
        log.warning("LLM produced no items, using English fallback")
        processed = fallback_processed(items)
    log.info("processed -> %d items after filter", len(processed))

    title = _make_title(mode)
    body = render_markdown(title, processed)

    os.makedirs("output", exist_ok=True)
    out_path = f"output/{mode}_{_now_ts()}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    log.info("digest written to %s", out_path)

    code = publish_pushplus(title, body, token=token, topic=topic)
    if code == 200:
        log.info("push ok")
    else:
        log.error("push failed status=%s", code)

    state.add([it.url for it in processed])
    state.save()
    return 0 if code == 200 else 2


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "evening"], required=True)
    args = parser.parse_args()
    sys.exit(run(args.mode))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sanity check (no network)**

```bash
python main.py --mode morning
```
Expected: exit 1 with "DEEPSEEK_API_KEY not set" (no key in env).

- [ ] **Step 3: Run full test suite**

```bash
pytest -q
```
Expected: all previous tests still pass (11+).

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): pipeline orchestration with state persistence"
```

---

## Task 8: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily.yml`

**Interfaces:**
- Runs twice daily
- Restores/saves `state.json` via artifact
- Uploads `output/*.md` as artifact

- [ ] **Step 1: Create `.github/workflows/daily.yml`**

```yaml
name: ai-news-daily

on:
  schedule:
    - cron: '0 0 * * *'   # 08:00 Asia/Shanghai
    - cron: '0 12 * * *'  # 20:00 Asia/Shanghai
  workflow_dispatch:
    inputs:
      mode:
        description: 'morning or evening'
        required: true
        default: 'morning'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Restore state
        uses: actions/download-artifact@v4
        with:
          name: ai-news-state
          path: .
        continue-on-error: true

      - name: Run pipeline
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          PUSHPLUS_TOKEN: ${{ secrets.PUSHPLUS_TOKEN }}
          PUSHPLUS_TOPIC: ${{ secrets.PUSHPLUS_TOPIC }}
          LLM_MODEL: ${{ secrets.LLM_MODEL }}
        run: |
          MODE="morning"
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            MODE="${{ inputs.mode }}"
          else
            hour=$(date -u +%H)
            if [ "$hour" -ge 12 ]; then MODE="evening"; fi
          fi
          python main.py --mode "$MODE"

      - name: Save state
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ai-news-state
          path: state.json

      - name: Save digest artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ai-news-output
          path: output/
```

- [ ] **Step 2: Create CI workflow `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest -q
```

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "ci: daily cron + push workflow"
```

---

## Task 9: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# AI 新闻微信聚合

每天两次自动抓取约 20 个 AI 信源，用 DeepSeek 翻译+评分+摘要，通过 PushPlus 推送到个人微信。

## 部署（5 分钟）

1. Fork 本仓库到你自己的 GitHub。
2. 注册 [pushplus.plus](https://pushplus.plus) 微信扫码绑定，拿到 `PUSHPLUS_TOKEN`。
3. 注册 [DeepSeek](https://platform.deepseek.com) 拿到 `DEEPSEEK_API_KEY`。
4. 在 fork 的仓库 **Settings → Secrets and variables → Actions** 新建：
   - `DEEPSEEK_API_KEY`
   - `PUSHPLUS_TOKEN`
   - （可选）`PUSHPLUS_TOPIC`、`LLM_MODEL`（默认 deepseek-chat）
5. 进入 **Actions** 页面启用 workflows。
6. （可选）配 [EasyCron](https://easycron.com) 等外部触发器以减少延迟。
7. （可选）本地试跑：`DEEPSEEK_API_KEY=... PUSHPLUS_TOKEN=... python main.py --mode morning`

## 配置项

| 环境变量 | 必填 | 默认 |
|---|---|---|
| `DEEPSEEK_API_KEY` | ✅ | - |
| `PUSHPLUS_TOKEN` | ✅ | - |
| `PUSHPLUS_TOPIC` | ❌ | - |
| `LLM_MODEL` | ❌ | `deepseek-chat` |

## 信源失效

如果某个 RSS URL 失效，编辑 `sources.py`，把对应行的 `url` 字段替换为新 RSS，提交后 Actions 自动生效。
失效的源会打印到 Actions 日志中：`source <name> fetch failed: ...`。

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate  # 或 .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

## 许可

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with deployment instructions"
```

---

## Self-Review

1. **Spec coverage:**
   - Sources list (~20) → Task 3
   - State persistence → Task 2
   - Fetcher with time-window + dedup → Task 4
   - LLM enrichment + filter + sort + top_n → Task 5 (threshold=6, top_n=15 hardcoded, override via param)
   - PushPlus markdown push → Task 6
   - Orchestration → Task 7
   - Cron + Secrets → Task 8
   - Tests for fetcher/processor/publisher → Tasks 4/5/6
   - State tests → Task 2
   - README with secrets setup → Task 9

2. **No placeholders:** No TBDs. All code shown.

3. **Type consistency:** `Item(url, title, source, snippet, published)` used uniformly. `Processed(url, title_zh, summary_zh, importance, category, source)` matches across processor/publisher. `enrich(items, api_key, model, base_url, top_n, importance_threshold)` signature used in Task 5 and Task 7 calls only positional `items, api_key, model`.

4. **Risk:** Cron timezone — `0 0 * * *` UTC = 08:00 CST. Recomputed → confirmed.
