from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_active_user
from app.db.session import get_db
from app.schemas.common import ok
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
async def summary(
    period: Literal["30d", "quarter", "year"] = "30d",
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Everything the dashboard needs in one call: KPIs with period-over-period change,
    12-month spend series, category / department / merchant breakdowns and insights.
    """
    return ok(await AnalyticsService(db).summary(user, period))


@router.get("/insights")
async def insights(
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Rule-based spending insights: budget pressure, missing receipts, duplicates, outliers, trends."""
    return ok({"insights": await AnalyticsService(db).insights(user)})
