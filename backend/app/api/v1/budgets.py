from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_active_user, require_finance_admin
from app.db.session import get_db
from app.schemas.budget import BudgetCopyRequest, BudgetUpsert
from app.schemas.common import ok
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("")
async def list_budgets(
    month: Optional[date] = None,
    include_unbudgeted: bool = True,
    _: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Budget vs. actual for every department in a month (defaults to the current month)."""
    items = await BudgetService(db).list(month or date.today(), include_unbudgeted=include_unbudgeted)
    return ok({"items": [b.model_dump(mode="json") for b in items]})


@router.put("")
async def upsert_budget(
    data: BudgetUpsert,
    _: CurrentUser = Depends(require_finance_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a department's budget for a month (finance admins)."""
    budget = await BudgetService(db).upsert(data)
    return ok({"budget": budget.model_dump(mode="json")})


@router.post("/copy")
async def copy_budgets(
    data: BudgetCopyRequest,
    _: CurrentUser = Depends(require_finance_admin),
    db: AsyncSession = Depends(get_db),
):
    """Copy all budgets from one month to another, e.g. to roll a plan forward."""
    return ok(await BudgetService(db).copy(data))


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: int,
    _: CurrentUser = Depends(require_finance_admin),
    db: AsyncSession = Depends(get_db),
):
    await BudgetService(db).delete(budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
