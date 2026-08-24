from unittest.mock import patch, MagicMock

from fetcher import Item
from processor import enrich, fallback_processed


def _fake_completion(content_str: str):
    return MagicMock(
        choices=[MagicMock(message=MagicMock(content=content_str))]
    )


def _ok_response(items: list[Item], start_imp: int = 9) -> str:
    rows = []
    for i, it in enumerate(items):
        rows.append(
            f'{{"url":"{it.url}","title_zh":"t{i}","summary_zh":"s{i}","importance":{start_imp - i},"category":"研究"}}'
        )
    return "[" + ",".join(rows) + "]"


def test_enrich_parses_json_and_filters():
    items = [
        Item(url="https://a/1", title="Big breakthrough", source="Test", snippet="x", published=None),
        Item(url="https://a/2", title="Minor update", source="Test", snippet="y", published=None),
    ]
    fake_json = (
        '[{"url":"https://a/1","title_zh":"重大突破","summary_zh":"一句话","importance":9,"category":"研究"},'
        '{"url":"https://a/2","title_zh":"小更新","summary_zh":"另一句","importance":3,"category":"产品"}]'
    )
    with patch("processor.OpenAI") as MockClient:
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
    with patch("processor.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _fake_completion(fake_json)
        result = enrich(items, api_key="k")
    assert result[0].url == "https://a/2"


def test_enrich_returns_empty_for_empty_items():
    with patch("processor.OpenAI") as MockClient:
        result = enrich([], api_key="k")
    assert result == []
    MockClient.return_value.chat.completions.create.assert_not_called()


def test_enrich_top_n_cap():
    items = [Item(url=f"https://a/{i}", title=f"t{i}", source="S", snippet="", published=None) for i in range(20)]
    fake_json = "[" + ",".join(
        f'{{"url":"https://a/{i}","title_zh":"t{i}","summary_zh":"x","importance":{10 - i // 2},"category":"研"}}'
        for i in range(20)
    ) + "]"
    with patch("processor.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _fake_completion(fake_json)
        result = enrich(items, api_key="k", top_n=5)
    assert len(result) == 5


def test_fallback_returns_processed_zero_importance():
    items = [Item(url="https://a/1", title="T", source="S", snippet="S", published=None)]
    result = fallback_processed(items)
    assert result[0].importance == 0
    assert result[0].title_zh == "T"


def test_enrich_passes_timeout_to_client():
    items = [Item(url="https://a/1", title="t", source="S", snippet="", published=None)]
    fake_json = '[{"url":"https://a/1","title_zh":"t","summary_zh":"s","importance":7,"category":"研究"}]'
    with patch("processor.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _fake_completion(fake_json)
        enrich(items, api_key="k")
    _, kwargs = MockClient.return_value.chat.completions.create.call_args
    assert kwargs.get("timeout") == 60.0


def test_enrich_batches_into_chunks_of_30():
    items = [Item(url=f"https://a/{i}", title=f"t{i}", source="S", snippet="", published=None) for i in range(45)]
    chunks_json = [
        _ok_response(items[0:30], start_imp=10),
        _ok_response(items[30:45], start_imp=10),
    ]
    responses = [_fake_completion(j) for j in chunks_json]

    with patch("processor.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.side_effect = responses
        enrich(items, api_key="k", top_n=50, importance_threshold=0)
    assert MockClient.return_value.chat.completions.create.call_count == 2


def test_enrich_falls_back_when_all_chunks_fail():
    items = [Item(url=f"https://a/{i}", title=f"t{i}", source="S", snippet="", published=None) for i in range(5)]
    with patch("processor.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.side_effect = RuntimeError("net down")
        result = enrich(items, api_key="k")
    assert len(result) == 5
    assert all(p.importance == 0 for p in result)