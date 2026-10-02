import os
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime


DEFAULT_TOPICS = [
    "AI tools people are using this week",
    "money mistakes people keep making",
    "new technology changing everyday life",
    "viral business stories",
    "personal finance myths",
]


def google_news_rss(query):
    url = "https://news.google.com/rss/search"

    response = requests.get(
        url,
        params={
            "q": query,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        },
        timeout=15,
        headers={
            "User-Agent": "MONEY-AI/1.0",
        },
    )

    response.raise_for_status()

    root = ET.fromstring(response.text)

    items = []

    for item in root.findall(".//item")[:15]:
        title = item.findtext("title")
        link = item.findtext("link")
        pub_date = item.findtext("pubDate")
        source_element = item.find("source")

        source = None
        if source_element is not None:
            source = source_element.text

        published_at = None

        if pub_date:
            try:
                published_at = parsedate_to_datetime(pub_date).isoformat()
            except Exception:
                published_at = pub_date

        if title and link:
            items.append(
                {
                    "title": title.strip(),
                    "url": link.strip(),
                    "source": source.strip() if source else None,
                    "published_at": published_at,
                }
            )

    return items


def score_trend(item):
    title = item.get("title", "").lower()

    score = 0

    high_value_words = [
        "ai",
        "artificial intelligence",
        "technology",
        "money",
        "business",
        "finance",
        "stocks",
        "market",
        "startup",
        "crypto",
        "robot",
        "apple",
        "google",
        "microsoft",
        "openai",
    ]

    for word in high_value_words:
        if word in title:
            score += 2

    attention_words = [
        "new",
        "breaking",
        "launch",
        "reveals",
        "revealed",
        "changes",
        "changed",
        "viral",
        "record",
        "huge",
        "why",
        "how",
        "future",
    ]

    for word in attention_words:
        if word in title:
            score += 1

    return score


def get_trend_candidates():
    query = os.getenv(
        "TREND_QUERY",
        "AI OR technology OR money OR business OR finance",
    )

    try:
        items = google_news_rss(query)

        if not items:
            raise RuntimeError("No trend results found")

        for item in items:
            item["score"] = score_trend(item)

        items.sort(
            key=lambda x: x.get("score", 0),
            reverse=True,
        )

        return items[:10]

    except Exception:
        return [
            {
                "title": topic,
                "url": None,
                "source": None,
                "published_at": None,
                "score": 0,
            }
            for topic in DEFAULT_TOPICS
        ]
