import logging
import time

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


def _business_code(resp: requests.Response) -> int | None:
    try:
        data = resp.json()
    except ValueError:
        return None
    code = data.get("code")
    try:
        return int(code) if code is not None else None
    except (TypeError, ValueError):
        return None


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
            if resp.status_code == 200:
                biz = _business_code(resp)
                if biz == 200:
                    log.info("pushplus ok: %s", resp.text[:200])
                    return 200
                last_err = RuntimeError(f"biz code {biz}")
                log.warning("pushplus biz code %s attempt %d: %s", biz, attempt + 1, resp.text[:200])
            elif resp.status_code == 429 or resp.status_code >= 500:
                last_err = RuntimeError(f"status {resp.status_code}")
                log.warning("pushplus %s attempt %d: %s", resp.status_code, attempt + 1, resp.text[:200])
            else:
                log.error("pushplus %s (no retry): %s", resp.status_code, resp.text[:200])
                return resp.status_code
        except Exception as exc:
            last_err = exc
            log.warning("pushplus attempt %d failed: %s", attempt + 1, exc)
        if attempt < 2:
            time.sleep(2 ** attempt)
    log.error("pushplus failed after retries: %s", last_err)
    return 0