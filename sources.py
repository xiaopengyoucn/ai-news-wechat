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