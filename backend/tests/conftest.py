"""
Test setup: a throwaway SQLite database (via aiosqlite) and upload directory,
configured through environment variables *before* the app is imported.
"""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="finai-tests-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256-signing"
os.environ["FRONTEND_URL"] = "http://testserver"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event, select  # noqa: E402

from app.core.rate_limit import login_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.init_db import seed_reference_data  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Base, Department, Role, User, UserRole  # noqa: E402

PASSWORD = "Password1"


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_fk_on(dbapi_conn, _):
    # SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


@pytest.fixture(autouse=True)
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_reference_data(session)
    login_limiter.clear()
    yield
    await engine.dispose()


async def create_user(email: str, roles: list[str], department: str | None = None, name: str | None = None) -> User:
    async with AsyncSessionLocal() as session:
        dept_id = None
        if department:
            dept_id = (await session.execute(select(Department.id).where(Department.name == department))).scalar_one()
        user = User(
            email=email,
            full_name=name or email.split("@")[0].title(),
            password_hash=hash_password(PASSWORD),
            department_id=dept_id,
        )
        session.add(user)
        await session.flush()
        for r in roles:
            role_id = (await session.execute(select(Role.id).where(Role.name == r))).scalar_one()
            session.add(UserRole(user_id=user.id, role_id=role_id))
        await session.commit()
        return user


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def login_as(email: str, roles: list[str] | None = None, department: str | None = None) -> AsyncClient:
    """Create a user (if roles given) and return a client holding their session cookies."""
    if roles is not None:
        await create_user(email, roles, department)
    client = make_client()
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return client


@pytest.fixture
async def client():
    async with make_client() as c:
        yield c


@pytest.fixture
async def employee():
    c = await login_as("emp@test.io", ["EMPLOYEE"], "Sales")
    yield c
    await c.aclose()


@pytest.fixture
async def employee2():
    c = await login_as("emp2@test.io", ["EMPLOYEE"], "Engineering")
    yield c
    await c.aclose()


@pytest.fixture
async def manager():
    c = await login_as("mgr@test.io", ["MANAGER"], "Sales")
    yield c
    await c.aclose()


@pytest.fixture
async def finance():
    c = await login_as("fin@test.io", ["FINANCE_ADMIN"])
    yield c
    await c.aclose()


@pytest.fixture
async def admin():
    c = await login_as("admin@test.io", ["SYSTEM_ADMIN"])
    yield c
    await c.aclose()
