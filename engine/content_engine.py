import json
import os
from openai import OpenAI

SYSTEM = """
You are MONEY AI, an expert short-form video content producer.

Return ONLY valid JSON with exactly these keys:
hook, script, caption, hashtags, visual_plan.

Create a factual, engaging 30-45 second vertical-video concept.

Rules:
- Never invent facts, statistics, quotes, events or people.
- If the topic is uncertain, say so.
- Use simple spoken language.
- The hook must grab attention without clickbait lies.
- The script must contain useful information, not generic filler.
- End with a clear takeaway.
- hashtags must be an array of strings.
- visual_plan must be an array of 5-7 concrete scene descriptions.
"""


def demo_content(topic):
    topic = topic.strip()

    return {
        "hook": f"Αξίζει πραγματικά την προσοχή σου το «{topic}»; Να τι πρέπει να ξέρεις.",
        "script": (
            f"Ας το δούμε απλά. Το θέμα είναι: {topic}. "
            "Πριν βγάλεις συμπέρασμα, ξεχώρισε τι είναι επιβεβαιωμένο "
            "από αυτό που είναι απλώς ισχυρισμός ή πρόβλεψη. "
            "Το σημαντικό είναι να καταλάβεις τι αλλάζει στην πράξη "
            "και ποιο είναι το βασικό συμπέρασμα. "
            "Κράτα λοιπόν τα δεδομένα και όχι τον θόρυβο."
        ),
        "caption": (
            f"Τι πρέπει πραγματικά να ξέρεις για: {topic}. "
            "Χωρίς υπερβολές και χωρίς να παρουσιάζουμε εικασίες ως γεγονότα."
        ),
        "hashtags": [
            "#moneyai",
            "#ai",
            "#technology",
            "#news",
            "#explained"
        ],
        "visual_plan": [
            f"Title card με το θέμα: {topic}",
            "Μεγάλο kinetic-text hook στην οθόνη",
            "Απλό visual που παρουσιάζει το βασικό θέμα",
            "Κείμενο στην οθόνη: Τι γνωρίζουμε",
            "Κείμενο στην οθόνη: Τι δεν γνωρίζουμε",
            "Σύντομο visual με το βασικό takeaway",
            "End card με MONEY AI"
        ]
    }


def generate_content(topic):
    topic = (topic or "").strip()

    if not topic:
        raise ValueError("Topic is required")

    api_key = os.getenv("OPENAI_API_KEY")

    # Free demo mode when no API key is available.
    if not api_key:
        return demo_content(topic)

    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
            instructions=SYSTEM,
            input=f"Topic: {topic}",
        )

        text = response.output_text.strip()
        data = json.loads(text)

        data.setdefault("hook", topic)
        data.setdefault("script", "")
        data.setdefault("caption", "")
        data.setdefault("hashtags", [])
        data.setdefault("visual_plan", [])

        return data

    except Exception:
        # If the API has no credits or is unavailable,
        # continue using the free demo generator.
        return demo_content(topic)
