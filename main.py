import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

load_dotenv()
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

class AuthCredentials(BaseModel):
    email: str | None = None
    password: str | None = None

@app.post("/auth/signup", status_code=201)
def signup(credentials: AuthCredentials):
    """Create a new user account via Supabase."""
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    result = supabase.auth.sign_up({
        "email": credentials.email,
        "password": credentials.password
    })
    return {"user": result.user}

@app.post("/auth/login")
def login(credentials: AuthCredentials):
    """Log in an existing user via Supabase and return their JWT."""
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token
    }

@app.get("/public/info")
def public_info():
    """Open endpoint — no auth required."""
    return {"message": "Welcome stranger! This info is public."}

def require_user(authorization: str | None = Header(default=None)):
    """Reusable auth guard: verifies the bearer token and returns the user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        result = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if result is None or result.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return result.user

@app.get("/protected/profile")
def protected_profile(user=Depends(require_user)):
    """Protected endpoint — requires a valid, verified bearer token."""
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at
    }

@app.post("/auth/logout", status_code=204)
def logout(user=Depends(require_user)):
    """Log out the current user (protected — requires a valid token)."""
    supabase.auth.sign_out()
    return

@app.get("/protected/dashboard")
def protected_dashboard(user=Depends(require_user)):
    """A second protected route, reusing the same guard — no new auth code."""
    return {"message": f"Welcome to your dashboard, {user.email}!"}

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
    return rows

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Get a single task by its ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row

@app.post("/tasks", status_code=201)
def create_task(new_task: TaskCreate):
    """Create a new task. Requires a non-empty title."""
    title = (new_task.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")

    conn = get_db()
    row = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
        (title, False)
    ).fetchone()
    conn.commit()
    conn.close()
    return row

@app.put("/tasks/{task_id}")
def update_task(task_id: int, updates: TaskUpdate):
    """Update a task's title and/or done status."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    new_title = row["title"]
    new_done = row["done"]

    if updates.title is not None:
        title = updates.title.strip()
        if not title:
            conn.close()
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        new_title = title

    if updates.done is not None:
        new_done = updates.done

    updated_row = conn.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
        (new_title, new_done, task_id)
    ).fetchone()
    conn.commit()
    conn.close()
    return updated_row

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task by its ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()
    return