# Fix Subagent Report — Review Findings (C1, C2, I1-I5, I7)

## Status
COMPLETE

## Test summary
24 passed (baseline 14 + 10 new). All green.

```
$ pytest -q
........................                                                 [100%]
24 passed in 0.46s
```

## Commit
- Hash: see `git log -1` output
- Message: `fix: address review findings (C1, C2, I1-I5, I7)`

## Fix map (file:line)

| ID | File:Line | Change |
|---|---|---|
| C1 | main.py:64-77 | `state.add`/`state.save` only inside `if code == 200`. Push failure now writes `output/failed_{ts}.md` with the full digest for manual retry. Returns exit code 2 instead of silently marking items as seen. |
| C2 | main.py:16, main.py:50-54 | New module constant `TOP_N = 15`. After fallback path, `processed = processed[:TOP_N]` enforces the spec's 15-item cap regardless of LLM jitter returning 100+ items. |
| I1 | fetcher.py:1-15, fetcher.py:42-48 | `fetch_one` now uses `requests.get(url, timeout=timeout, headers={"User-Agent": "ai-news-wechat/0.1"})` and feeds `resp.content` into `feedparser.parse`. Timeout actually reaches the socket now; UA header added to avoid opaque 403s. |
| I2 | processor.py:6, processor.py:71, processor.py:77-80 | `timeout=60.0` passed to `client.chat.completions.create`. `openai.APITimeoutError` is now imported and caught explicitly so the retry doc-string matches behavior. Generic `Exception` retained for other failures. |
| I3 | publisher.py:66, publisher.py:78-79, publisher.py:85-86 | `range(3)` keeps 1 initial + 2 retries (matches spec "重试 2 次"). Exponential backoff `time.sleep(2 ** attempt)` after each failure. HTTP 429 explicitly routed to the retry branch alongside 5xx. |
| I4 | publisher.py:36-46, publisher.py:68-76 | New `_business_code(resp)` helper parses `resp.json().get("code")`. The retry loop now only returns `200` when **both** HTTP status is 200 **and** PushPlus business code is 200. Non-200 business codes drive `last_err` and backoff just like 5xx. Non-retryable 4xx (e.g. 401) returns immediately with the status code. |
| I5 | processor.py:24, processor.py:83-88, processor.py:100-113 | New `_CHUNK_SIZE = 20` constant. New `_enrich_chunk` helper retries per-chunk (2 attempts, 60s timeout). `enrich` splits into chunks of 20, calls LLM per chunk, merges results. Fallback engages only when **all** chunks fail — partial success keeps the successful chunks' rows. |
| I7 | sources.py:10 | Added `{"name": "Papers with Code AI", "url": "https://paperswithcode.com/area/ai/feed", "region": "en"}` between arXiv cs.LG and Hacker News. Source list now 21. |

## Test additions

### test_fetcher.py (+1)
- `test_fetch_one_passes_timeout` — asserts `timeout` and `User-Agent` reach `requests.get`.

Existing 3 tests updated to mock `fetcher.requests.get` (with `.content` + `raise_for_status`) alongside `feedparser.parse`, since `fetch_one` now makes a real HTTP call before parsing.

### test_processor.py (+3)
- `test_enrich_passes_timeout_to_client` — asserts `timeout=60.0` on `chat.completions.create`.
- `test_enrich_batches_into_chunks_of_20` — 45 items → 3 LLM calls; result capped at `top_n=15`.
- `test_enrich_falls_back_when_all_chunks_fail` — full LLM outage still triggers fallback.

### test_publisher.py (+5)
- `test_publish_pushplus_retries_on_5xx_then_succeeds` — 503 → 200, exactly 1 sleep(1).
- `test_publish_pushplus_retries_on_429` — 429 → 200, exactly 1 sleep(1).
- `test_publish_pushplus_uses_exponential_backoff` — asserts `sleep(1)` then `sleep(2)`.
- `test_publish_pushplus_returns_0_after_all_retries_fail` — 3×503 ⇒ `0`.
- `test_publish_pushplus_treats_biz_code_failure_as_retry` — HTTP 200 + code=903 ⇒ retry, success on 2nd.
- `test_publish_pushplus_returns_status_on_non_retry_4xx` — 401 ⇒ single attempt, no sleep.

Existing 2 tests updated: success-path mocks now provide `json=lambda: {"code": 200}` so the business-code gate returns 200.

## Files changed
- main.py
- fetcher.py
- processor.py
- publisher.py
- sources.py
- tests/test_fetcher.py
- tests/test_processor.py
- tests/test_publisher.py

## Notes
- Minor findings M1-M12 deliberately left untouched per the brief.
- retry semantics now align with spec §错误处理 ("PushPlus HTTP 失败：重试 2 次（指数回退），最终失败写到 output/failed_<timestamp>.md").
- LLM retry path also aligns with spec ("LLM 整批失败：重试 1 次") — `_enrich_chunk` does exactly 2 attempts.