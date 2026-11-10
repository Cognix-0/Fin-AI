"""User administration (SYSTEM_ADMIN only)."""
from __future__ import annotations

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.core.errors import bad_request, conflict, not_found
from app.models.models import Department
from app.repositories.user_repository import UserRepository
from app.schemas.user import VALID_ROLES, UserAdminUpdate
from app.services.auth_service import AuthService


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)
        self.auth = AuthService(session)

    async def list(self, *, search: str | None, page: int, page_size: int) -> dict:
        users, total = await self.repo.list(search=search, offset=(page - 1) * page_size, limit=page_size)
        return {
            "items": [self.auth.to_response(u).model_dump(mode="json") for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, math.ceil(total / page_size)),
        }

    async def update(self, user_id: uuid.UUID, data: UserAdminUpdate, actor: CurrentUser) -> dict:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise not_found("User")
        is_self = user.id == actor.id
        currently_admin = "SYSTEM_ADMIN" in self.repo.get_role_names(user)

        if data.roles is not None:
            roles = sorted({r.strip().upper() for r in data.roles})
            invalid = [r for r in roles if r not in VALID_ROLES]
            if invalid:
                raise bad_request("UNKNOWN_ROLE", f"Unknown role(s): {', '.join(invalid)}")
            if currently_admin and "SYSTEM_ADMIN" not in roles:
                if is_self:
                    raise conflict("SELF_LOCKOUT", "You cannot remove your own admin role")
                if await self.repo.count_with_role("SYSTEM_ADMIN") <= 1:
                    raise conflict("LAST_ADMIN", "At least one active system admin is required")
            await self.repo.set_roles(user, roles)

        if data.department is not None:
            if data.department.strip() == "":
                user.department_id = None
            else:
                dept = (await self.session.execute(
                    select(Department).where(func.lower(Department.name) == data.department.strip().lower())
                )).scalar_one_or_none()
                if not dept:
                    raise bad_request("UNKNOWN_DEPARTMENT", f"Unknown department '{data.department}'")
                user.department_id = dept.id

        if data.is_active is not None and data.is_active != user.is_active:
            if not data.is_active:
                if is_self:
                    raise conflict("SELF_LOCKOUT", "You cannot deactivate your own account")
                if currently_admin and await self.repo.count_with_role("SYSTEM_ADMIN") <= 1:
                    raise conflict("LAST_ADMIN", "At least one active system admin is required")
                # Kill their sessions straight away
                await self.repo.revoke_all_refresh_tokens(user.id)
            user.is_active = data.is_active

        await self.session.flush()
        self.session.expire(user)            # user_id comes from the URL, so no lazy load here
        user = await self.repo.get_by_id(user_id)
        return self.auth.to_response(user).model_dump(mode="json")
