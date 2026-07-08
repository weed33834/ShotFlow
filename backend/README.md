# ShotFlow backend

FastAPI + SQLAlchemy 2.0 + Celery backend that wraps the `08_Automation/` generation
scripts into a REST + SSE API with a render queue.

## Stack

- **FastAPI** — async REST API, Swagger / ReDoc auto-docs
- **SQLAlchemy 2.0** — ORM, Alembic migrations
- **Celery + Redis** — render queue, async tasks
- **PostgreSQL** (prod) / **SQLite** (dev/test) — switchable via `DATABASE_URL`
- **JWT (PyJWT) + bcrypt** — auth, RBAC (admin / director / art_director / algo_engineer / video_operator / post_lead / sound_designer / qa / ops / pm / member)

## Layout

```
backend/
├── app/
│   ├── api/v1/          # route handlers (projects, shots, keyframes, queue, ...)
│   ├── core/            # config, security
│   ├── db/              # session, base
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # business logic (ComfyUI, Kling, queue, ...)
│   ├── tasks/           # Celery tasks
│   └── main.py          # app factory
├── alembic/             # DB migrations
├── tests/               # pytest suite (179 tests, SQLite in-memory)
├── requirements.txt
├── Dockerfile
└── init_db.py           # schema + seed
```

## Quick start

```bash
# from repo root
docker compose up -d                       # PostgreSQL + Redis + backend + worker
docker compose exec backend python init_db.py --seed
# Swagger: http://localhost:8000/docs
# Health:  http://localhost:8000/api/v1/health
```

Or run locally without Docker:

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt        # pytest, ruff, black, isort
DATABASE_URL="sqlite:///./shotflow.db" alembic upgrade head
DATABASE_URL="sqlite:///./shotflow.db" python init_db.py --seed
uvicorn app.main:app --reload --port 8000
```

## Configuration

All settings read from the repo-root `.env` (see [`.env.example`](../.env.example) and
[`app/core/config.py`](./app/core/config.py)). Key flags:

- `SIMULATE_MODE=true` — every generation service returns mock output, no GPU needed
- `DEBUG=true` — relaxes the `SECRET_KEY` guard for local dev
- `DATABASE_URL` — `postgresql+psycopg://...` (prod) or `sqlite:///./shotflow.db` (dev)

## Tests

```bash
cd backend
python -m pytest tests/ -q
```

Tests use in-memory SQLite and need no external services. See the test files under
`backend/tests/` for the full suite layout.

## API overview

See the root [README.md](../README.md#web-platform) for the route table. Swagger UI at
`/docs` is the canonical reference.
