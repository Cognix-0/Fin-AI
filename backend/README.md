# Fin-AI Backend

FastAPI service with async SQLAlchemy (asyncpg), Alembic migrations, and JWT auth.

## Features

- **Auth**: register, login, logout, profile update, password change. Uses short-lived
  access tokens plus rotating refresh tokens in HTTP-only cookies. Replaying an old refresh
  token revokes all of that user's sessions. Failed logins are throttled per IP and email.
- **Expenses**: draft → pending → approved / rejected workflow, with an audit trail,
  withdraw, edit-and-resubmit after rejection, bulk approve/reject, search, filters,
  sorting, pagination and CSV export.
- **Approvals**: role- and department-aware. Nobody can review their own expense, and
  department managers only see and review their department's expenses.
- **Receipts**: PNG, JPG, WebP or PDF up to 10 MB. The type is checked from file contents,
  not the declared type. Files are stored outside the web root with random names.
- **Budgets**: monthly limit per department, with budget-vs-actual figures (approved and
  pending) and a copy-month-forward helper.
- **Analytics**: KPIs with period-over-period change, a 12-month trend, breakdowns by
  category, department and merchant, and rule-based insights. Insights flag budget
  overruns, missing receipts, stale approvals, possible duplicates, outliers and
  category trends.
- **User admin**: system admins can change roles, departments and active status. Changes
  take effect on the user's next request.
- **Ops**: consistent JSON error envelope, request IDs, access logs, security headers,
  gzip, and liveness/readiness probes. The app refuses to start in production with a
  weak `JWT_SECRET`.

## Prerequisites

- Python 3.12+
- PostgreSQL running locally (or reachable via `DATABASE_URL`)

## Setup

Run these from the `backend/` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Then edit `.env`: set `DATABASE_URL` to your database and replace `JWT_SECRET` with a long random value.

## Database migrations

```bash
alembic upgrade head
```

The Docker image runs this automatically on start (set `RUN_MIGRATIONS=false` to disable).

## Demo data (optional)

```bash
python -m app.db.seed_demo
```

Creates users for every role (password `Demo1234!`), 12 months of budgets, and about
500 expenses so the dashboard has data to show. With Docker Compose:

```bash
docker compose exec backend python -m app.db.seed_demo
```

| Email | Roles | Department |
|---|---|---|
| admin@finai.demo | System admin, Finance admin | — |
| finance@finai.demo | Finance admin | Operations |
| manager@finai.demo | Manager | Sales |
| eng.manager@finai.demo | Manager | Engineering |
| priya@finai.demo | Employee | Sales |

## Run the server

```bash
uvicorn app.main:app --reload
```

- Health check: http://localhost:8000/api/v1/health (plus `/health/live` and `/health/ready`)
- Interactive API docs (non-production only): http://localhost:8000/docs

## API overview

All responses use `{"success": true, "data": ...}`, and errors use
`{"success": false, "error": {"code", "message"}}`.

| Method & path | Who | Purpose |
|---|---|---|
| `POST /auth/register` · `/login` · `/logout` · `/refresh` | anyone | Session management (cookies) |
| `GET/PATCH /auth/me`, `POST /auth/change-password` | signed in | Own profile |
| `GET /expenses` | signed in | List with `status, category, department, search, date_from, date_to, min_amount, max_amount, mine, missing_receipt, sort, page, page_size` |
| `GET /expenses/export` | signed in | Same filters, CSV download |
| `POST /expenses` | signed in | Create (`submit: true` to send for approval) |
| `GET/PATCH/DELETE /expenses/{id}` | owner (edit/delete: draft or rejected) | Read / edit / delete |
| `POST /expenses/{id}/submit` · `/withdraw` | owner | Workflow |
| `POST /expenses/{id}/approve` · `/reject` | manager, finance | Review (`reject` needs a `reason`) |
| `POST /expenses/bulk-decision` | manager, finance | Approve/reject many at once |
| `GET /expenses/{id}/history` | anyone who can see it | Audit trail |
| `POST/GET/DELETE /expenses/{id}/receipt` | owner uploads; viewers download | Receipt file |
| `GET /budgets?month=YYYY-MM-DD` | signed in | Budget vs actual per department |
| `PUT /budgets`, `POST /budgets/copy`, `DELETE /budgets/{id}` | finance | Manage budgets |
| `GET /analytics/summary?period=30d\|quarter\|year` | signed in | Dashboard data (scoped to what you can see) |
| `GET /analytics/insights` | signed in | Insights only |
| `GET /meta` | signed in | Categories, departments, statuses, roles |
| `GET /users`, `PATCH /users/{id}` | system admin | User administration |

## Tests

```bash
pytest
```

Tests use a throwaway SQLite database through `aiosqlite`, so they don't need PostgreSQL.
