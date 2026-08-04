# devin-projects

A small FastAPI todo service used as a sandbox for practicing Devin workflows: delegating tickets, fixing CI, and iterating on playbooks against a real codebase.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

| Task | Command |
| --- | --- |
| Run the API | `uvicorn todo_api.main:app --reload --app-dir src` |
| Run tests | `pytest -q` |
| Lint | `ruff check .` |
| Format | `ruff format .` |

Interactive API docs are at `http://localhost:8000/docs` once the server is running.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| GET | `/todos` | List todos |
| POST | `/todos` | Create a todo (`{"title": "...", "done": false}`) |
| GET | `/todos/{id}` | Fetch one todo |
| PATCH | `/todos/{id}` | Update title and/or done |
| DELETE | `/todos/{id}` | Delete a todo |

Storage is in-memory, so data resets when the process restarts.

## CI

GitHub Actions runs `ruff check`, `ruff format --check`, and `pytest` on every pull request.
