# Fin-AI Backend

FastAPI service with async SQLAlchemy (asyncpg), Alembic migrations, and JWT auth.

## Prerequisites

- Python 3
- PostgreSQL running locally (or reachable via `DATABASE_URL`)

## Setup

Run these from the `backend/` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env`: set `DATABASE_URL` to your database and replace `JWT_SECRET` with a long random value.

## Database migrations

```bash
alembic upgrade head
```

## Run the server

```bash
uvicorn app.main:app --reload
```

- Health check: http://localhost:8000/api/v1/health
- Interactive API docs (non-production only): http://localhost:8000/docs

## Tests

```bash
pytest
```
