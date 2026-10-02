import os
import requests
import xml.etree.ElementTree as ET

DEFAULT_TOPICS = [
    "AI tools people are using this week",
    "money mistakes people keep making",
    "new technology changing everyday life",
    "viral business stories",
    "personal finance myths",
]

def google_news_rss(query):
    url = "https://news.google.com/rss/search"
    r = requests.get(url, params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}, timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    items = []
    for item in root.findall(".//item")[:10]:
        title = item.findtext("title")
        link = item.findtext("link")
        if title:
            items.append({"title": title, "url": link})
    return items

def get_trend_candidates():
    query = os.getenv("TREND_QUERY", "AI OR technology OR money OR business")
    try:
        items = google_news_rss(query)
        if items:
            return items
    except Exception:
        pass
    return [{"title": x, "url": None} for x in DEFAULT_TOPICS]
