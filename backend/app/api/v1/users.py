import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, require_admin
from app.db.session import get_db
from app.schemas.common import ok
from app.schemas.user import UserAdminUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User administration"])


@router.get("")
async def list_users(
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return ok(await UserService(db).list(search=search, page=page, page_size=page_size))


@router.patch("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    data: UserAdminUpdate,
    actor: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's roles, department or active status."""
    return ok({"user": await UserService(db).update(user_id, data, actor)})
