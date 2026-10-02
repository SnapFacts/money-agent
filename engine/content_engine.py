import json
import os
import re
import html
import requests

from openai import OpenAI


SYSTEM = """
You are MONEY AI, an expert short-form video producer.

Return ONLY valid JSON with exactly these keys:
hook, script, caption, hashtags, visual_plan.

Create a factual 30-45 second vertical video.

Rules:
- Never invent facts, statistics, quotes, events or people.
- Use only information supported by the supplied source material.
- Do not turn predictions or opinions into facts.
- Hook must create curiosity without lying.
- Script must be specific and useful.
- Use short spoken sentences.
- Explain why the story matters.
- End with a clear takeaway.
- hashtags must be an array of strings.
- visual_plan must contain 6-8 concrete visual scenes.
"""


def clean_text(text):
    if not text:
        return ""

    text = html.unescape(str(text))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_meta(html_text, attribute, value):
    pattern = (
        r'<meta[^>]+'
        + attribute
        + r'=["\']'
        + re.escape(value)
        + r'["\'][^>]+'
        r'content=["\']([^"\']+)'
    )

    match = re.search(
        pattern,
        html_text,
        re.IGNORECASE,
    )

    if match:
        return clean_text(match.group(1))

    reverse_pattern = (
        r'<meta[^>]+'
        r'content=["\']([^"\']+)["\'][^>]+'
        + attribute
        + r'=["\']'
        + re.escape(value)
        + r'["\']'
    )

    match = re.search(
        reverse_pattern,
        html_text,
        re.IGNORECASE,
    )

    if match:
        return clean_text(match.group(1))

    return ""


def fetch_source(url):
    if not url:
        return {}

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; MONEY-AI/1.0)"
                )
            },
        )

        response.raise_for_status()

        html_text = response.text

        title = ""
        description = ""
        image_url = ""
        site_name = ""

        title = extract_meta(
            html_text,
            "property",
            "og:title",
        )

        description = extract_meta(
            html_text,
            "property",
            "og:description",
        )

        image_url = extract_meta(
            html_text,
            "property",
            "og:image",
        )

        site_name = extract_meta(
            html_text,
            "property",
            "og:site_name",
        )

        if not title:
            title = extract_meta(
                html_text,
                "name",
                "twitter:title",
            )

        if not description:
            description = extract_meta(
                html_text,
                "name",
                "description",
            )

        if not image_url:
            image_url = extract_meta(
                html_text,
                "name",
                "twitter:image",
            )

        if not title:
            title_match = re.search(
                r"<title[^>]*>(.*?)</title>",
                html_text,
                re.IGNORECASE | re.DOTALL,
            )

            if title_match:
                title = clean_text(
                    title_match.group(1)
                )

        return {
            "title": title,
            "description": description,
            "image_url": image_url,
            "site_name": site_name,
        }

    except Exception as exc:
        print(
            f"[MONEY AI] Source fetch failed: {exc}",
            flush=True,
        )

        return {}


def demo_content(
    topic,
    source_url=None,
    source_name=None,
    published_at=None,
):
    topic = clean_text(topic)

    source = fetch_source(source_url)

    real_title = (
        source.get("title")
        or topic
    )

    description = (
        source.get("description")
        or ""
    )

    source_label = (
        source.get("site_name")
        or source_name
        or "Source"
    )

    if description:
        script = (
            f"Η είδηση είναι αυτή: {real_title}. "
            f"{description} "
            "Το σημαντικό είναι να ξεχωρίσουμε "
            "τι έχει επιβεβαιωθεί από το τι αποτελεί "
            "πρόβλεψη ή σχόλιο. "
            "Για αυτό αξίζει να κοιτάξεις την αρχική πηγή "
            "και τα πραγματικά δεδομένα πριν βγάλεις συμπέρασμα."
        )
    else:
        script = (
            f"Το θέμα που αξίζει να προσέξεις είναι: "
            f"{real_title}. "
            f"Η διαθέσιμη πληροφορία από το {source_label} "
            "δείχνει ότι πρόκειται για εξέλιξη που αξίζει "
            "να παρακολουθήσουμε. "
            "Το βασικό ερώτημα είναι τι έχει επιβεβαιωθεί "
            "και τι παραμένει άγνωστο."
        )

    return {
        "hook": (
            "Αυτή η είδηση τραβάει την προσοχή — "
            "αλλά το σημαντικό σημείο είναι άλλο."
        ),
        "script": script,
        "caption": (
            f"{real_title}. "
            "Τα βασικά σημεία, με βάση την διαθέσιμη πηγή."
        ),
        "hashtags": [
            "#moneyai",
            "#news",
            "#business",
            "#technology",
            "#ai",
            "#explained",
        ],
        "visual_plan": [
            "Opening με το headline της είδησης",
            "Εμφάνιση της βασικής εικόνας της πηγής",
            "Zoom στο σημαντικό σημείο",
            "Source card",
            "Animated explanation",
            "What we know",
            "What remains unknown",
            "Final takeaway",
        ],
        "source": {
            "url": source_url,
            "name": source_name,
            "site_name": source_label,
            "title": real_title,
            "image_url": source.get("image_url"),
            "description": description,
            "published_at": published_at,
        },
    }


def generate_content(
    topic,
    source_url=None,
    source_name=None,
    published_at=None,
):
    topic = (topic or "").strip()

    if not topic:
        raise ValueError("Topic is required")

    source_page = fetch_source(source_url)

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return demo_content(
            topic,
            source_url=source_url,
            source_name=source_name,
            published_at=published_at,
        )

    try:
        client = OpenAI(
            api_key=api_key
        )

        source_material = {
            "topic": topic,
            "source_url": source_url,
            "source_name": source_name,
            "published_at": published_at,
            "source_title": source_page.get(
                "title"
            ),
            "source_description": source_page.get(
                "description"
            ),
        }

        response = client.responses.create(
            model=os.getenv(
                "OPENAI_MODEL",
                "gpt-6-luna",
            ),
            instructions=SYSTEM,
            input=(
                "Create the video from this "
                "source material:\n\n"
                + json.dumps(
                    source_material,
                    ensure_ascii=False,
                    indent=2,
                )
            ),
        )

        text = response.output_text.strip()

        data = json.loads(text)

        data.setdefault(
            "hook",
            topic,
        )

        data.setdefault(
            "script",
            "",
        )

        data.setdefault(
            "caption",
            "",
        )

        data.setdefault(
            "hashtags",
            [],
        )

        data.setdefault(
            "visual_plan",
            [],
        )

        data["source"] = {
            "url": source_url,
            "name": source_name,
            "site_name": (
                source_page.get(
                    "site_name"
                )
                or source_name
            ),
            "title": (
                source_page.get(
                    "title"
                )
                or topic
            ),
            "image_url": source_page.get(
                "image_url"
            ),
            "description": source_page.get(
                "description"
            ),
            "published_at": published_at,
        }

        return data

    except Exception as exc:
        print(
            f"[MONEY AI] OpenAI generation failed: {exc}",
            flush=True,
        )

        return demo_content(
            topic,
            source_url=source_url,
            source_name=source_name,
            published_at=published_at,
        )
