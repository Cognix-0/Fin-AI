from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import Money


class BudgetUpsert(BaseModel):
    department: str = Field(min_length=1, max_length=100)
    month: date = Field(description="Any day in the target month; normalised to the 1st")
    amount_limit: Decimal = Field(ge=0, le=Decimal("100000000"), max_digits=12, decimal_places=2)


class BudgetCopyRequest(BaseModel):
    from_month: date
    to_month: date
    overwrite: bool = False


class BudgetOut(BaseModel):
    id: int | None            # None when a department has no budget set for the month
    department: str
    month: date
    limit: Money
    spent: Money              # approved expenses
    pending: Money            # submitted, awaiting approval
    remaining: Money
    utilization: float        # spent / limit * 100 (0 when no limit)
    status: str               # on_track | near_limit | over_budget | no_budget
