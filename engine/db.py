import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("MONEY_AI_DB", "money_ai.db")

connect = lambda: sqlite3.connect(DB_PATH)

def init_db():
c = connect()
c.execute("CREATE TABLE IF NOT EXISTS content_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, content_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)")
c.commit()
c.close()

def create_content_job(topic, content):
c = connect()
cur = c.execute("INSERT INTO content_jobs(topic, content_json, status, created_at) VALUES (?, ?, ?, ?)", (topic, json.dumps(content, ensure_ascii=False), "content_ready", datetime.now(timezone.utc).isoformat()))
c.commit()
job_id = cur.lastrowid
c.close()
return job_id

def update_job_status(job_id, status):
c = connect()
c.execute("UPDATE content_jobs SET status=? WHERE id=?", (status, job_id))
c.commit()
c.close()

def get_job(job_id):
c = connect()
row = c.execute("SELECT * FROM content_jobs WHERE id=?", (job_id,)).fetchone()
c.close()
if not row:
return None
d = dict(zip(["id", "topic", "content_json", "status", "created_at"], row))
d["content"] = json.loads(d.pop("content_json"))
return d

def list_jobs(limit=50):
c = connect()
rows = c.execute("SELECT * FROM content_jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
c.close()
out = []
for row in rows:
d = dict(zip(["id", "topic", "content_json", "status", "created_at"], row))
d["content"] = json.loads(d.pop("content_json"))
out.append(d)
return out
