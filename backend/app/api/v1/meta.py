from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_active_user
from app.db.session import get_db
from app.models.models import Category, Department, ExpenseStatus
from app.schemas.common import ok
from app.schemas.user import VALID_ROLES

router = APIRouter(prefix="/meta", tags=["Reference data"])


@router.get("")
async def reference_data(
    _: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Lookup lists for forms and filters: categories, departments, statuses and roles."""
    categories = (await db.execute(
        select(Category.name).where(Category.is_active.is_(True)).order_by(Category.name)
    )).scalars().all()
    departments = (await db.execute(select(Department.name).order_by(Department.name))).scalars().all()
    return ok({
        "categories": list(categories),
        "departments": list(departments),
        "statuses": [s.value for s in ExpenseStatus],
        "roles": list(VALID_ROLES),
    })
