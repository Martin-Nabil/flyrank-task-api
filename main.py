import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Task API",
    description="A simple SQLite-backed CRUD API for managing to-do tasks.",
    version="2.0"
)

DB_FILE = "tasks.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [("Buy milk", 0), ("Walk the dog", 0), ("Finish assignment", 1)]
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
    for task in tasks:
        if task["id"] == task_id:
            if updates.title is not None:
                title = updates.title.strip()
                if not title:
                    raise HTTPException(status_code=400, detail="Title cannot be empty")
                task["title"] = title
            if updates.done is not None:
                task["done"] = updates.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task by its ID."""
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")