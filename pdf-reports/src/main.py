import sqlite3
import uuid
import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="PDF Report Generator")

DB_FILE = "reports.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            pdf_path TEXT,
            error TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

class ReportCreatedResponse(BaseModel):
    report_id: str
    status: str

@app.post("/reports", status_code=202, response_model=ReportCreatedResponse)
def create_report():
    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO reports (id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (report_id, "pending", now, now)
    )
    conn.commit()
    conn.close()

    return ReportCreatedResponse(report_id=report_id, status="pending")