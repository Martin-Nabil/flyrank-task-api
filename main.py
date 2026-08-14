import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

app = FastAPI(
    title="Task API",
    description="A Postgres-backed CRUD API for managing to-do tasks.",
    version="3.0"
)

DATABASE_URL = os.environ["DATABASE_URL"]

def get_db():
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT false
        )
    """)
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()["count"]
    if count == 0:
        conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s), (%s, %s), (%s, %s)",
            ("Buy milk", False, "Walk the dog", False, "Finish assignment", True)
        )
    conn.commit()
    conn.close()

init_db()

class TaskCreate(BaseModel):
    title: str | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None
@app.get("/")
def root():
    """Basic info about this API."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/tasks")
def get_tasks():
    """List all tasks."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Get a single task by its ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return dict(row)

@app.post("/tasks", status_code=201)
def create_task(new_task: TaskCreate):
    """Create a new task. Requires a non-empty title."""
    title = (new_task.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")

    conn = get_db()
    cursor = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, 0))
    conn.commit()
    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)

@app.put("/tasks/{task_id}")
def update_task(task_id: int, updates: TaskUpdate):
    """Update a task's title and/or done status."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    current = dict(row)
    new_title = current["title"]
    new_done = current["done"]

    if updates.title is not None:
        title = updates.title.strip()
        if not title:
            conn.close()
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        new_title = title

    if updates.done is not None:
        new_done = 1 if updates.done else 0

    conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (new_title, new_done, task_id)
    )
    conn.commit()
    updated_row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(updated_row)

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task by its ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return