from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid

from app.models.models import User, Role, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email (case-insensitive), eager-loading their roles."""
        result = await self.session.execute(
            select(User)
            .where(User.email == email.lower().strip())
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch a user by UUID, eager-loading their roles."""
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str, full_name: str) -> User:
        """Create a new user (does not assign roles — use assign_role after)."""
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name.strip(),
        )
        self.session.add(user)
        await self.session.flush()   # get the id before commit
        return user

    async def assign_role(self, user: User, role_name: str) -> None:
        """Assign a named role to a user. Silently skips if role doesn't exist."""
        result = await self.session.execute(
            select(Role).where(Role.name == role_name)
        )
        role = result.scalar_one_or_none()
        if not role:
            raise ValueError(f"Role '{role_name}' not found in database. Run init_db first.")
        user_role = UserRole(user_id=user.id, role_id=role.id)
        self.session.add(user_role)

    def get_role_names(self, user: User) -> list[str]:
        """Extract role name strings from a user's loaded user_roles."""
        return [ur.role.name for ur in user.user_roles if ur.role]
