import os
from engine.trend_engine import get_trend_candidates
from engine.content_engine import generate_content
from engine.db import create_content_job

def main():
    topics = get_trend_candidates()
    limit = int(os.getenv("MONEY_AI_DAILY_GENERATIONS", "3"))
    for item in topics[:limit]:
        title = item["title"]
        content = generate_content(title)
        job_id = create_content_job(title, content)
        print(f"created job {job_id}: {title}")

if __name__ == "__main__":
    main()
