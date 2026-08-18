SOURCES = [
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml", "region": "en"},
    {"name": "Google DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml", "region": "en"},
    {"name": "BAIR Blog", "url": "https://bair.berkeley.edu/blog/feed.xml", "region": "en"},
    {"name": "arXiv cs.AI", "url": "https://export.arxiv.org/rss/cs.AI", "region": "en"},
    {"name": "arXiv cs.CL", "url": "https://export.arxiv.org/rss/cs.CL", "region": "en"},
    {"name": "arXiv cs.LG", "url": "https://export.arxiv.org/rss/cs.LG", "region": "en"},
    {"name": "Hacker News (AI)", "url": "https://hnrss.org/newest?q=AI", "region": "en"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "region": "en"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "region": "en"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "region": "en"},
    {"name": "The Decoder", "url": "https://the-decoder.com/feed/", "region": "en"},
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "region": "zh"},
]


def get_sources() -> list[dict]:
    return SOURCES
