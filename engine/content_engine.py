import json
import os
from openai import OpenAI

SYSTEM = """
You are MONEY AI, an expert short-form video content producer.
Return ONLY valid JSON with exactly these keys:
hook, script, caption, hashtags, visual_plan.
Create a punchy vertical-video concept. Keep the script concise enough for about
30-45 seconds. Hashtags must be an array of strings. visual_plan must be an array
of short scene descriptions. Do not claim facts you cannot support. If a topic is
uncertain or current, phrase it cautiously.
"""

def fallback(topic):
    return {
        "hook": f"Το θέμα που συζητούν όλοι: {topic}",
        "script": (
            f"Σε 30 δευτερόλεπτα, αυτό είναι που πρέπει να ξέρεις για {topic}. "
            "Ξεκίνα με το βασικό γεγονός, εξήγησε γιατί έχει σημασία και κλείσε "
            "με μία καθαρή takeaway πρόταση."
        ),
        "caption": f"Αυτό είναι το βασικό που πρέπει να ξέρεις για {topic}.",
        "hashtags": ["#fyp", "#viral", "#moneyai"],
        "visual_plan": ["bold hook", "3 key points", "final takeaway"],
    }

def generate_content(topic):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback(topic)

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        instructions=SYSTEM,
        input=f"Topic: {topic}",
    )
    text = response.output_text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return fallback(topic)

    data.setdefault("hook", topic)
    data.setdefault("script", "")
    data.setdefault("caption", "")
    data.setdefault("hashtags", [])
    data.setdefault("visual_plan", [])
    return data
