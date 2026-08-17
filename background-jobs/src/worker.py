import os
import sqlite3
import json
import time
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_FILE = "jobs.db"
PROMPT_VERSION = "enrich-v1"
POLL_INTERVAL_SECONDS = 2

with open(f"prompts/{PROMPT_VERSION}.md", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL"),
    api_key=os.environ.get("LLM_API_KEY")
)

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group())

def call_model(title: str, description: str) -> dict:
    user_content = json.dumps({"title": title, "description": description})
    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        timeout=30.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
    )
    raw_text = response.choices[0].message.content
    return extract_json(raw_text)

def claim_next_job(conn) -> sqlite3.Row | None:
    """Find one pending job and mark it as running, atomically."""
    row = conn.execute(
        "SELECT * FROM jobs WHERE status = 'pending' ORDER BY created_at LIMIT 1"
    ).fetchone()

    if row is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE jobs SET status = 'running', updated_at = ? WHERE id = ? AND status = 'pending'",
        (now, row["id"])
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],)).fetchone()
    if updated["status"] != "running":
        return None

    return updated

MAX_ATTEMPTS = 3

def log_alert(job_id, error, attempts):
    """A basic alert: append to a file a human would monitor."""
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "error": error,
        "attempts": attempts,
        "message": f"Job {job_id} permanently failed after {attempts} attempts"
    }
    with open("logs/alerts.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"ALERT: {entry['message']}")

def process_job(conn, job):
    input_data = json.loads(job["input"])
    now = datetime.now(timezone.utc).isoformat()
    attempts = job["attempts"] + 1

    try:
        result = call_model(input_data["title"], input_data["description"])
        conn.execute(
            "UPDATE jobs SET status = 'completed', result = ?, attempts = ?, updated_at = ? WHERE id = ?",
            (json.dumps(result), attempts, now, job["id"])
        )
        print(f"COMPLETED job {job['id']}")

    except Exception as e:
        if attempts < MAX_ATTEMPTS:
            backoff = 2 ** attempts
            print(f"RETRY {attempts}/{MAX_ATTEMPTS} for job {job['id']} in {backoff}s: {e}")
            conn.execute(
                "UPDATE jobs SET status = 'pending', attempts = ?, error = ?, updated_at = ? WHERE id = ?",
                (attempts, str(e), now, job["id"])
            )
            conn.commit()
            time.sleep(backoff)
            return

        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ?, attempts = ?, updated_at = ? WHERE id = ?",
            (str(e), attempts, now, job["id"])
        )
        conn.commit()
        log_alert(job["id"], str(e), attempts)
        return

    conn.commit()

def run_worker():
    print("Worker started, polling for jobs...")
    while True:
        conn = get_db()
        job = claim_next_job(conn)
        if job:
            print(f"CLAIMED job {job['id']}")
            process_job(conn, job)
        conn.close()
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker()