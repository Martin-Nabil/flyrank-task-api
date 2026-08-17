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

@app.post("/jobs", status_code=202, response_model=JobCreatedResponse)
def create_job(payload: JobRequest):
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO jobs (id, status, input, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (job_id, "pending", json.dumps(payload.model_dump()), now, now)
    )
    conn.commit()
    conn.close()

    return JobCreatedResponse(job_id=job_id, status="pending")