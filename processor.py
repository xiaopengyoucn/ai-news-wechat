import json
import logging
import re
from dataclasses import dataclass

from openai import APITimeoutError, OpenAI

from fetcher import Item


log = logging.getLogger(__name__)

_SCI_BOOST_KEYWORDS = (
    "polymer", "polymerization", "monomer", "oligomer",
    "composite", "composites", "fiberglass", "fibreglass", "carbon fiber", "carbon fibre",
    "catalyst", "catalysis", "catalytic",
    "electrolyte", "electrolytes", "anode", "cathode",
    "battery", "lithium", "sodium-ion", "solid-state",
    "alloy", "alloys", "intermetallic",
    "crystal", "crystalline", "ceramic", "ceramics",
    "synthesis", "synthesize", "synthesized",
    "polymerization", "polycondensation", "crosslink",
    "membrane", "separator", "electrolyte",
    "electrocatalyst", "electrocatalysis",
    "organic", "inorganic", "organometallic",
    "nanoparticle", "nanotube", "nanofiber", "nanocomposite",
    "self-assembly", "self-assembled",
    "photosynthesis", "photochemistry",
    "polyimide", "epoxy", "resin", "thermoplastic", "thermoset",
    "elastomer", "rubber", "silicone",
    "纤维", "复合材料", "高分子", "聚合物", "单体",
    "催化", "催化剂", "电解液", "锂电", "电池",
    "合金", "晶体", "陶瓷", "合成",
    "纳米", "树脂", "橡胶", "硅胶",
)

_BOOST_AMOUNT = 1

_AI_KEYWORDS = (
    # English
    "machine learning", "deep learning", "neural network", "graph neural",
    "transformer", "diffusion model", "language model", "large language model",
    "llm", "ml ", "ml-", " ml.", "(ml)",
    "AI-driven", "AI-powered", "AI-based", "AI-assisted", "AI-enabled",
    "AI model", "ML model", "foundation model",
    "deepmind", "alphafold", "alphaproteo",
    "predict", "prediction", "computational design", "in silico",
    "molecular dynamics", "monte carlo", "simulation",
    # Chinese
    "人工智能", "机器学习", "深度学习", "神经网络",
    "大模型", "AI 模型", "AI模型", "AI 驱动", "AI驱动",
    "AI 辅助", "AI辅助", "深度神经网络", "图神经网络",
    "AI 预测", "AI预测", "分子动力学", "模拟",
)

_COMPANY_BOOST_KEYWORDS = (
    "晶泰", "XtalPi", "晶泰科技",
    "深势", "深势科技", "DP Technology",
    "Citrine", "Kebotix", "Atinary",
    "智谱", "Zhipu", "GLM",
    "百川", "百川智能", "Baichuan",
    "Kimi", "月之暗面", "Moonshot",
    "通义", "通义千问", "Qwen",
    "文心一言", "百度", "Baidu", "ERNIE",
    "豆包", "字节跳动", "ByteDance", "Doubao",
    "混元", "腾讯", "Tencent", "Hunyuan",
    "盘古", "华为", "Huawei", "Pangu",
    "DeepSeek", "深度求索",
    "阶跃", "StepFun",
    "稀宇科技", "MiniMax",
    "上海人工智能实验室", "Shanghai AI Lab",
)

_CHINESE_SOURCE_NAMES = ("量子位", "机器之心", "36氪", "新智元")


def _tier_score(p: "Processed") -> int:
    text = (p.title_zh + " " + p.summary_zh).lower()
    has_chem = any(kw.lower() in text for kw in _SCI_BOOST_KEYWORDS)
    has_company = any(kw in (p.title_zh + p.summary_zh) for kw in _COMPANY_BOOST_KEYWORDS)
    has_ai = any(kw.lower() in text for kw in _AI_KEYWORDS)
    if has_company:
        return 1
    if has_chem and has_ai:
        return 1
    if has_ai and not has_chem:
        return 2
    if has_chem and not has_ai:
        return 3
    return 3


@dataclass
class Processed:
    url: str
    title_zh: str
    summary_zh: str
    importance: int
    category: str
    source: str
    image_url: str | None = None


_CHUNK_SIZE = 30

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

        title_zh = str(row.get("title_zh") or "")
        summary_zh = str(row.get("summary_zh") or "")
        haystack = (title_zh + " " + summary_zh).lower()
        for kw in _SCI_BOOST_KEYWORDS:
            if kw.lower() in haystack:
                importance = min(10, importance + _BOOST_AMOUNT)
                break
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
                image_url=it.image_url,
            )
        )

    processed.sort(key=lambda p: (_tier_score(p), -p.importance))
    return processed[:top_n]


def fallback_processed(items: list[Item], top_n: int = 15) -> list[Processed]:
    processed = [
        Processed(
            url=it.url,
            title_zh=it.title,
            summary_zh=it.snippet[:80] if it.snippet else "(无摘要)",
            importance=0,
            category="原始",
            source=it.source,
            image_url=it.image_url,
        )
        for it in items
    ]
    processed.sort(key=lambda p: (_tier_score(p), -p.importance))
    return processed[:top_n]