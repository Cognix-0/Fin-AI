"""
Database initialisation — seeds default roles on first run.
Run once after migrations: python -m app.db.init_db
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import Role

DEFAULT_ROLES = [
    {"name": "EMPLOYEE", "description": "Standard employee — can create and submit expenses"},
    {"name": "MANAGER", "description": "Team manager — can review and approve team expenses"},
    {"name": "FINANCE_ADMIN", "description": "Finance administrator — can manage all financial data"},
    {"name": "SYSTEM_ADMIN", "description": "System administrator — full platform access"},
]


async def seed_roles(session: AsyncSession) -> None:
    for role_data in DEFAULT_ROLES:
        result = await session.execute(
            select(Role).where(Role.name == role_data["name"])
        )
        existing = result.scalar_one_or_none()
        if not existing:
            role = Role(**role_data)
            session.add(role)
    await session.commit()
    print("✅ Default roles seeded.")


async def init_db() -> None:
    async with AsyncSessionLocal() as session:
        await seed_roles(session)


if __name__ == "__main__":
    asyncio.run(init_db())
