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
    {"name": "Nature Chemistry", "url": "https://www.nature.com/nchem.rss", "region": "en"},
    {"name": "Nature Materials", "url": "https://www.nature.com/nmat.rss", "region": "en"},
    {"name": "Nature Computational Science", "url": "https://www.nature.com/subjects/computational-science.rss", "region": "en"},
    {"name": "arXiv cond-mat.soft", "url": "https://export.arxiv.org/rss/cond-mat.soft", "region": "en"},
    {"name": "arXiv cond-mat.mtrl-sci", "url": "https://export.arxiv.org/rss/cond-mat.mtrl-sci", "region": "en"},
    {"name": "arXiv q-bio.BM", "url": "https://export.arxiv.org/rss/q-bio.BM", "region": "en"},
    {"name": "Phys.org Chemistry", "url": "https://phys.org/rss-feed/chemistry-news/", "region": "en"},
]


def get_sources() -> list[dict]:
    return SOURCES