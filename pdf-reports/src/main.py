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

IDEMPOTENCY_WINDOW_MINUTES = 5

@app.post("/reports", status_code=202, response_model=ReportCreatedResponse)
def create_report():
    conn = get_db()

    recent = conn.execute(
        """SELECT id, status FROM reports
           WHERE status IN ('pending', 'running', 'completed')
           ORDER BY created_at DESC LIMIT 1"""
    ).fetchone()

    if recent:
        created = conn.execute("SELECT created_at FROM reports WHERE id = ?", (recent["id"],)).fetchone()
        created_time = datetime.fromisoformat(created["created_at"])
        age_minutes = (datetime.now(timezone.utc) - created_time).total_seconds() / 60

        if age_minutes < IDEMPOTENCY_WINDOW_MINUTES:
            conn.close()
            return ReportCreatedResponse(report_id=recent["id"], status=recent["status"])

    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO reports (id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (report_id, "pending", now, now)
    )
    conn.commit()
    conn.close()

    return ReportCreatedResponse(report_id=report_id, status="pending")

class ReportStatusResponse(BaseModel):
    report_id: str
    status: str
    download_url: str | None = None
    error: str | None = None
    attempts: int
    created_at: str
    updated_at: str

@app.get("/reports/{report_id}", response_model=ReportStatusResponse)
def get_report(report_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    download_url = f"/reports/{report_id}/download" if row["status"] == "completed" else None

    return ReportStatusResponse(
        report_id=row["id"],
        status=row["status"],
        download_url=download_url,
        error=row["error"],
        attempts=row["attempts"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

@app.get("/reports/{report_id}/download")
def download_report(report_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    if row["status"] != "completed" or not row["pdf_path"]:
        raise HTTPException(status_code=409, detail=f"Report is not ready yet (status: {row['status']})")

    return FileResponse(
        path=row["pdf_path"],
        media_type="application/pdf",
        filename=f"report-{report_id}.pdf"
    )