from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Task API",
    description="A simple in-memory CRUD API for managing to-do tasks.",
    version="1.0"
)

tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Walk the dog", "done": False},
    {"id": 3, "title": "Finish assignment", "done": True},
]

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
    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Get a single task by its ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.post("/tasks", status_code=201)
def create_task(new_task: TaskCreate):
    """Create a new task. Requires a non-empty title."""
    title = (new_task.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")

    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {"id": next_id, "title": title, "done": False}
    tasks.append(task)
    return task

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