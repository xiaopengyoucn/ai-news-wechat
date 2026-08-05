from unittest.mock import patch, MagicMock

from processor import Processed
from publisher import render_markdown, publish_pushplus


def _items():
    return [
        Processed(url="https://a/1", title_zh="突破", summary_zh="一句话", importance=9, category="研究", source="OpenAI"),
        Processed(url="https://a/2", title_zh="更新", summary_zh="一句话2", importance=7, category="产品", source="Anthropic"),
    ]


def _ok_resp():
    return MagicMock(status_code=200, text="ok", json=lambda: {"code": 200})


def test_render_markdown_contains_title_and_urls():
    md = render_markdown("AI 早报", _items())
    assert "AI 早报" in md
    assert "https://a/1" in md
    assert "https://a/2" in md
    assert "## 研究" in md
    assert "## 产品" in md
    assert "突破" in md


def test_publish_pushplus_posts_to_correct_url():
    with patch("publisher.requests.post") as mock_post:
        mock_post.return_value = _ok_resp()
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
        mock_post.return_value = _ok_resp()
        publish_pushplus("hi", "body", token="tok", topic="mygroup")
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["topic"] == "mygroup"


def test_publish_pushplus_retries_on_5xx_then_succeeds():
    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.time.sleep") as mock_sleep:
        mock_post.side_effect = [
            MagicMock(status_code=503, text="down", json=lambda: {}),
            MagicMock(status_code=200, text="ok", json=lambda: {"code": 200}),
        ]
        code = publish_pushplus("hi", "body", token="tok")
    assert code == 200
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(1)


def test_publish_pushplus_retries_on_429():
    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.time.sleep") as mock_sleep:
        mock_post.side_effect = [
            MagicMock(status_code=429, text="rl", json=lambda: {}),
            MagicMock(status_code=200, text="ok", json=lambda: {"code": 200}),
        ]
        code = publish_pushplus("hi", "body", token="tok")
    assert code == 200
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(1)


def test_publish_pushplus_uses_exponential_backoff():
    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.time.sleep") as mock_sleep:
        mock_post.side_effect = [
            MagicMock(status_code=500, text="e1", json=lambda: {}),
            MagicMock(status_code=500, text="e2", json=lambda: {}),
            MagicMock(status_code=200, text="ok", json=lambda: {"code": 200}),
        ]
        publish_pushplus("hi", "body", token="tok")
    assert [c.args for c in mock_sleep.call_args_list] == [(1,), (2,)]


def test_publish_pushplus_returns_0_after_all_retries_fail():
    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.time.sleep"):
        mock_post.side_effect = [
            MagicMock(status_code=503, text="e1", json=lambda: {}),
            MagicMock(status_code=503, text="e2", json=lambda: {}),
            MagicMock(status_code=503, text="e3", json=lambda: {}),
        ]
        code = publish_pushplus("hi", "body", token="tok")
    assert code == 0
    assert mock_post.call_count == 3


def test_publish_pushplus_treats_biz_code_failure_as_retry():
    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.time.sleep"):
        mock_post.side_effect = [
            MagicMock(status_code=200, text="biz fail", json=lambda: {"code": 903, "msg": "rate"}),
            MagicMock(status_code=200, text="ok", json=lambda: {"code": 200}),
        ]
        code = publish_pushplus("hi", "body", token="tok")
    assert code == 200
    assert mock_post.call_count == 2


def test_publish_pushplus_returns_status_on_non_retry_4xx():
    with patch("publisher.requests.post") as mock_post, \
         patch("publisher.time.sleep") as mock_sleep:
        mock_post.return_value = MagicMock(status_code=401, text="auth", json=lambda: {"code": 401})
        code = publish_pushplus("hi", "body", token="tok")
    assert code == 401
    assert mock_post.call_count == 1
    mock_sleep.assert_not_called()