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

TOP_N = 15


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
        processed = processed[:TOP_N]
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
        state.add([it.url for it in processed])
        state.save()
        return 0

    log.error("push failed status=%s", code)
    failed_path = f"output/failed_{_now_ts()}.md"
    with open(failed_path, "w", encoding="utf-8") as f:
        f.write(body)
    log.error("digest preserved at %s for manual retry", failed_path)
    return 2


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