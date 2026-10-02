import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("MONEY_AI_DB", "money_ai.db")

connect = lambda: sqlite3.connect(DB_PATH)

def_dummy = None

def_exec = lambda sql, args=(): (lambda c: (c.execute(sql, args), c.commit(), c.close()))(connect())

init_db = lambda: def_exec("CREATE TABLE IF NOT EXISTS content_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, content_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)")

create_content_job = lambda topic, content: (lambda c: (lambda cur: (c.commit(), cur.lastrowid, c.close())[1])(c.execute("INSERT INTO content_jobs(topic, content_json, status, created_at) VALUES (?, ?, ?, ?)", (topic, json.dumps(content, ensure_ascii=False), "content_ready", datetime.now(timezone.utc).isoformat()))))(connect())

update_job_status = lambda job_id, status: (lambda c: (c.execute("UPDATE content_jobs SET status=? WHERE id=?", (status, job_id)), c.commit(), c.close()))(connect())

get_job = lambda job_id: (lambda c: (lambda row: (c.close(), None if not row else dict(zip(["id", "topic", "content_json", "status", "created_at"], row))))(c.execute("SELECT * FROM content_jobs WHERE id=?", (job_id,)).fetchone()))(connect())

list_jobs = lambda limit=50: (lambda c: (lambda rows: (c.close(), [dict(zip(["id", "topic", "content_json", "status", "created_at"], row)) for row in rows][1]))(c.execute("SELECT * FROM content_jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()))(connect())

init_db()
