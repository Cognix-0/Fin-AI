from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import RefreshToken, Role, User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _with_roles(self):
        return select(User).options(selectinload(User.user_roles).selectinload(UserRole.role))

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email (case-insensitive), eager-loading their roles."""
        result = await self.session.execute(
            self._with_roles().where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch a user by UUID, eager-loading their roles."""
        result = await self.session.execute(self._with_roles().where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list(
        self, *, search: Optional[str] = None, offset: int = 0, limit: int = 50,
    ) -> tuple[list[User], int]:
        stmt = self._with_roles()
        count_stmt = select(func.count()).select_from(User)
        if search:
            like = f"%{search.lower().strip()}%"
            cond = func.lower(User.full_name).like(like) | User.email.like(like)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        total = (await self.session.execute(count_stmt)).scalar_one()
        rows = await self.session.execute(stmt.order_by(User.full_name).offset(offset).limit(limit))
        return list(rows.scalars().unique()), total

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
        """Assign a named role to a user. Raises if the role doesn't exist."""
        role = await self.get_role(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found in database. Run migrations first.")
        self.session.add(UserRole(user_id=user.id, role_id=role.id))

    async def get_role(self, role_name: str) -> Optional[Role]:
        result = await self.session.execute(select(Role).where(Role.name == role_name))
        return result.scalar_one_or_none()

    async def set_roles(self, user: User, role_names: list[str]) -> None:
        """Replace a user's roles with exactly `role_names` (user must have roles loaded)."""
        result = await self.session.execute(select(Role).where(Role.name.in_(role_names)))
        roles = {r.id: r for r in result.scalars()}
        missing = set(role_names) - {r.name for r in roles.values()}
        if missing:
            raise ValueError(f"Unknown role(s): {', '.join(sorted(missing))}")
        # Diff against current roles so unchanged rows are left alone
        for ur in list(user.user_roles):
            if ur.role_id not in roles:
                user.user_roles.remove(ur)       # delete-orphan cascade removes the row
        current = {ur.role_id for ur in user.user_roles}
        for role_id, role in roles.items():
            if role_id not in current:
                user.user_roles.append(UserRole(user_id=user.id, role_id=role_id, role=role))
        await self.session.flush()

    async def count_with_role(self, role_name: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .join(User, User.id == UserRole.user_id)
            .where(Role.name == role_name, User.is_active.is_(True))
        )
        return result.scalar_one()

    def get_role_names(self, user: User) -> list[str]:
        """Extract role name strings from a user's loaded user_roles."""
        return sorted(ur.role.name for ur in user.user_roles if ur.role)

    # ── Refresh tokens ────────────────────────────────────────────────────────

    async def add_refresh_token(self, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> None:
        self.session.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at))
        await self.session.flush()

    async def get_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_all_refresh_tokens(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True),
            execution_options={"synchronize_session": "fetch"},
        )

    async def purge_expired_refresh_tokens(self, user_id: uuid.UUID) -> None:
        """Housekeeping so the table doesn't grow forever."""
        await self.session.execute(
            delete(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.expires_at < datetime.now(timezone.utc),
            ),
            execution_options={"synchronize_session": False},
        )
