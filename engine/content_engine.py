import json
import os
import re
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

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_source(url):
    if not url:
        return {}

    try:
        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 MONEY-AI/1.0"
            },
        )

        response.raise_for_status()

        html = response.text

        title = ""
        description = ""

        title_match = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
            html,
            re.IGNORECASE,
        )

        if title_match:
            title = clean_text(title_match.group(1))

        description_match = re.search(
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
            html,
            re.IGNORECASE,
        )

        if description_match:
            description = clean_text(description_match.group(1))

        if not title:
            title_match = re.search(
                r"<title[^>]*>(.*?)</title>",
                html,
                re.IGNORECASE | re.DOTALL,
            )

            if title_match:
                title = clean_text(title_match.group(1))

        return {
            "title": title,
            "description": description,
        }

    except Exception:
        return {}


def demo_content(topic, source_url=None, source_name=None):
    topic = clean_text(topic)

    source = fetch_source(source_url)

    real_title = source.get("title") or topic
    description = source.get("description") or ""

    source_label = source_name or "Source"

    if description:
        script = (
            f"Αυτό είναι το θέμα που συζητιέται τώρα: {real_title}. "
            f"{description} "
            "Το σημαντικό εδώ είναι να ξεχωρίσουμε την είδηση "
            "από τις προβλέψεις και τις υπερβολές. "
            "Αν αυτή η εξέλιξη συνεχιστεί, το βασικό ερώτημα είναι "
            "τι σημαίνει στην πράξη για τους ανθρώπους και την αγορά. "
            "Κράτα την πηγή και έλεγξε τα δεδομένα πριν βγάλεις συμπέρασμα."
        )
    else:
        script = (
            f"Μια νέα εξέλιξη τραβάει την προσοχή: {real_title}. "
            f"Η διαθέσιμη πληροφορία από το {source_label} "
            "δείχνει ότι πρόκειται για θέμα που αξίζει να παρακολουθήσουμε. "
            "Δεν θα παρουσιάσουμε προβλέψεις ως γεγονότα. "
            "Το βασικό είναι να δούμε τι έχει επιβεβαιωθεί, "
            "τι παραμένει άγνωστο και τι μπορεί να αλλάξει στην πράξη. "
            "Αυτό είναι το σημείο που αξίζει να κρατήσεις."
        )

    return {
        "hook": f"Αυτό συμβαίνει τώρα — και μπορεί να έχει μεγαλύτερη σημασία απ' όσο φαίνεται.",
        "script": script,
        "caption": (
            f"{real_title}. "
            "Τα βασικά σημεία, χωρίς clickbait και χωρίς να παρουσιάζουμε "
            "εικασίες ως γεγονότα."
        ),
        "hashtags": [
            "#moneyai",
            "#ai",
            "#technology",
            "#business",
            "#news",
            "#explained",
        ],
        "visual_plan": [
            f"Opening shot με headline: {real_title}",
            "Γρήγορο zoom στο βασικό σημείο της είδησης",
            "Source card με το όνομα της πηγής",
            "Animated text με το σημαντικότερο γεγονός",
            "Visual που εξηγεί γιατί έχει σημασία",
            "Σύντομο section: Τι γνωρίζουμε",
            "Σύντομο section: Τι δεν έχει επιβεβαιωθεί",
            "Final takeaway με MONEY AI branding",
        ],
        "source": {
            "url": source_url,
            "name": source_name,
            "title": real_title,
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

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return demo_content(
            topic,
            source_url=source_url,
            source_name=source_name,
        )

    try:
        client = OpenAI(api_key=api_key)

        source_material = {
            "topic": topic,
            "source_url": source_url,
            "source_name": source_name,
            "published_at": published_at,
        }

        source_page = fetch_source(source_url)

        if source_page:
            source_material["source_title"] = source_page.get("title")
            source_material["source_description"] = source_page.get(
                "description"
            )

        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
            instructions=SYSTEM,
            input=(
                "Create the video from this source material:\n\n"
                + json.dumps(
                    source_material,
                    ensure_ascii=False,
                    indent=2,
                )
            ),
        )

        text = response.output_text.strip()
        data = json.loads(text)

        data.setdefault("hook", topic)
        data.setdefault("script", "")
        data.setdefault("caption", "")
        data.setdefault("hashtags", [])
        data.setdefault("visual_plan", [])

        data["source"] = {
            "url": source_url,
            "name": source_name,
            "title": topic,
        }

        return data

    except Exception:
        return demo_content(
            topic,
            source_url=source_url,
            source_name=source_name,
        )
