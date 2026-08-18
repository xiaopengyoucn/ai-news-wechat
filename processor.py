import json
import logging
import re
from dataclasses import dataclass

from openai import APITimeoutError, OpenAI

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


_CHUNK_SIZE = 20

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


def _enrich_chunk(client: OpenAI, items: list[Item], model: str) -> list[dict] | None:
    prompt = _build_prompt(items)
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=60.0,
            )
            parsed = _parse_json_block(resp.choices[0].message.content or "")
            if parsed is not None:
                return parsed
            last_err = ValueError("parse failed")
        except APITimeoutError as exc:
            last_err = exc
            log.warning("LLM timeout attempt %d: %s", attempt + 1, exc)
        except Exception as exc:
            last_err = exc
            log.warning("LLM call attempt %d failed: %s", attempt + 1, exc)
    log.error("LLM chunk failed after retries (n=%d): %s", len(items), last_err)
    return None


def enrich(
    items: list[Item],
    api_key: str,
    model: str = "deepseek-v4-flash",
    base_url: str = "https://api.deepseek.com/v1",
    top_n: int = 15,
    importance_threshold: int = 6,
) -> list[Processed]:
    if not items:
        return []

    client = OpenAI(api_key=api_key, base_url=base_url)

    chunks = [items[i:i + _CHUNK_SIZE] for i in range(0, len(items), _CHUNK_SIZE)]
    all_rows: list[dict] = []
    failed_chunks = 0
    for chunk in chunks:
        parsed = _enrich_chunk(client, chunk, model)
        if parsed is None:
            failed_chunks += 1
            continue
        all_rows.extend(parsed)

    if failed_chunks == len(chunks):
        log.error("LLM failed for all chunks, using fallback")
        return fallback_processed(items)

    by_url = {it.url: it for it in items}
    processed: list[Processed] = []
    for row in all_rows:
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