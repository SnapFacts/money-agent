```python
import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("MONEY_AI_DB", "money_ai.db")


def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with connect() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS content_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            content_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        c.commit()


def create_content_job(topic, content):
    with connect() as c:
        cur = c.execute(
            """
            INSERT INTO content_jobs
            (topic, content_json, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                topic,
                json.dumps(content, ensure_ascii=False),
                "content_ready",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        c.commit()
        return cur.lastrowid


def update_job_status(job_id, status):
    with connect() as c:
        c.execute(
            "UPDATE content_jobs SET status=? WHERE id=?",
            (status, job_id),
        )
        c.commit()


def get_job(job_id):
    with connect() as c:
        row = c.execute(
            "SELECT * FROM content_jobs WHERE id=?",
            (job_id,),
        ).fetchone()

    if not row:
        return None

    d = dict(row)
    d["content"] = json.loads(d.pop("content_json"))
    return d


def list_jobs(limit=50):
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM content_jobs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    out = []

    for row in rows:
        d = dict(row)
        d["content"] = json.loads(d.pop("content_json"))
        out.append(d)

    return out
```
