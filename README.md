# Task API

A simple in-memory CRUD API for managing a to-do list, built with **Python** and **FastAPI**.

This project was built for the FlyRank Internship — Backend Track, Week 2, Assignment A1.

## What it is

The API lets a client create, read, update, and delete tasks. Each task has:

- `id` — number
- `title` — text
- `done` — true/false

Data is stored in a local SQLite database (tasks.db), so it survives server restarts.
The database and table are created automatically on first run.
## How to install

1. Clone this repository:
```bash
   git clone https://github.com/Martin-Nabil/flyrank-task-api.git
   cd flyrank-task-api
```

2. Create and activate a virtual environment:
```bash
   python -m venv venv
   venv\Scripts\Activate.ps1      # Windows (PowerShell)
   source venv/bin/activate       # macOS/Linux
```

3. Install dependencies:
```bash
   pip install fastapi uvicorn
```

## How to run

```bash
uvicorn main:app --reload --port 8000
```

The server will start at `http://localhost:8000`.

Interactive Swagger UI docs are available at: http://localhost:8000/docs

## Endpoints

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| GET | `/` | API info | 200 | — |
| GET | `/health` | Health check | 200 | — |
| GET | `/tasks` | List all tasks | 200 | — |
| GET | `/tasks/{id}` | Get a single task | 200 | 404 if not found |
| POST | `/tasks` | Create a new task | 201 | 400 if title missing/empty |
| PUT | `/tasks/{id}` | Update a task's title and/or done status | 200 | 404 if not found, 400 if title empty |
| DELETE | `/tasks/{id}` | Delete a task | 204 | 404 if not found |

## Example request

Create a new task:

```bash
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "{\"title\":\"Buy milk\"}"
```

Example response: 
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}

## Swagger UI

Full endpoint list:

![Swagger UI endpoint list](swagger-list.png)

Successfully executing a request via "Try it out":

![Swagger UI try it out](swagger-execute.png)

## Notes

- Data is stored in memory using a plain Python list — it resets on every server restart. This is expected for this stage of the project; persistent storage (a database) is planned for a later assignment.
## Database

This project now uses **SQLite** instead of in-memory storage.

Why SQLite:
- Single file — no separate database server to install or run
- Zero setup — the database and table are created automatically on first run
- Data survives restarts, unlike Assignment 1's in-memory list

Where it lives:
- `tasks.db` is created automatically in the project root the first time the app starts
- It is **git-ignored** — each fresh clone starts with a clean database, auto-seeded with 3 example tasks
- No manual database setup is required; just run the app

### Start command

```bash
uvicorn main:app --reload --port 8000
```

This single command creates `tasks.db`, creates the `tasks` table if missing, and seeds 3 example tasks if the table is empty.

### DB Browser for SQLite

![DB Browser showing the tasks table](db-browser.png)

### Example manual SQL query

```sql
UPDATE tasks SET done = 1;
```

Marks every task as completed at once. Run through DB Browser's Execute SQL tab and "Write Changes," this change was visible immediately through `GET /tasks` — no server restart needed, since the API and DB Browser read the same `tasks.db` file.