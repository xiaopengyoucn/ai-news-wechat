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
    assert "## 研究" in md
    assert "## 产品" in md
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