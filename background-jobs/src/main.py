import os
import sqlite3
import uuid
import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Background Jobs")

DB_FILE = "jobs.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            input TEXT NOT NULL,
            result TEXT,
            error TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

class JobRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=0, max_length=3000)

class JobCreatedResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None
    attempts: int
    created_at: str
    updated_at: str

@app.post("/jobs", status_code=202, response_model=JobCreatedResponse)
def create_job(payload: JobRequest):
    input_json = json.dumps(payload.model_dump(), sort_keys=True)

    conn = get_db()

    existing = conn.execute(
        "SELECT id, status FROM jobs WHERE input = ? AND status IN ('pending', 'running', 'completed') ORDER BY created_at DESC LIMIT 1",
        (input_json,)
    ).fetchone()

    if existing:
        conn.close()
        return JobCreatedResponse(job_id=existing["id"], status=existing["status"])

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO jobs (id, status, input, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (job_id, "pending", input_json, now, now)
    )
    conn.commit()
    conn.close()

    return JobCreatedResponse(job_id=job_id, status="pending")

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    result = json.loads(row["result"]) if row["result"] else None

    return JobStatusResponse(
        job_id=row["id"],
        status=row["status"],
        result=result,
        error=row["error"],
        attempts=row["attempts"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )