"""
Database initialisation — seeds reference data (roles, departments, categories).
Migrations already do this; the script is idempotent and safe to re-run.

    python -m app.db.init_db
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.models import Category, Department, Role

DEFAULT_ROLES = [
    {"name": "EMPLOYEE", "description": "Standard employee — can create and submit expenses"},
    {"name": "MANAGER", "description": "Team manager — can review and approve team expenses"},
    {"name": "FINANCE_ADMIN", "description": "Finance administrator — can manage all financial data"},
    {"name": "SYSTEM_ADMIN", "description": "System administrator — full platform access"},
]
DEFAULT_DEPARTMENTS = ["Engineering", "Sales", "Marketing", "Operations"]
DEFAULT_CATEGORIES = ["Travel", "Software", "Meals", "Office", "Marketing", "Utilities"]


async def seed_reference_data(session: AsyncSession) -> None:
    existing_roles = set((await session.execute(select(Role.name))).scalars())
    for role in DEFAULT_ROLES:
        if role["name"] not in existing_roles:
            session.add(Role(**role))

    existing_depts = set((await session.execute(select(Department.name))).scalars())
    for name in DEFAULT_DEPARTMENTS:
        if name not in existing_depts:
            session.add(Department(name=name))

    existing_cats = set((await session.execute(select(Category.name))).scalars())
    for name in DEFAULT_CATEGORIES:
        if name not in existing_cats:
            session.add(Category(name=name))

    await session.commit()


# Backwards-compatible name
seed_roles = seed_reference_data


async def init_db() -> None:
    async with AsyncSessionLocal() as session:
        await seed_reference_data(session)
    print("Reference data seeded (roles, departments, categories).")


if __name__ == "__main__":
    asyncio.run(init_db())
