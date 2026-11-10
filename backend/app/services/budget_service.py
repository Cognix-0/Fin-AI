"""
Monthly department budgets.

`spent` counts approved expenses; `pending` counts submitted ones still awaiting
review. Utilisation and status use both ("committed" spend), so a budget shows
as at risk before the money is actually approved.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import bad_request, not_found
from app.models.models import Budget, Department, Expense, ExpenseStatus
from app.schemas.budget import BudgetCopyRequest, BudgetOut, BudgetUpsert
from app.services.dates import add_months, month_start

NEAR_LIMIT_PCT = 85.0
ZERO = Decimal("0")


def budget_status(limit: Decimal | None, committed: Decimal) -> tuple[float, str]:
    if limit is None:
        return 0.0, "no_budget"
    if limit == 0:
        return (0.0, "on_track") if committed == 0 else (100.0, "over_budget")
    pct = float(committed / limit * 100)
    if pct > 100:
        return pct, "over_budget"
    if pct >= NEAR_LIMIT_PCT:
        return pct, "near_limit"
    return pct, "on_track"


class BudgetService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _department(self, name: str) -> Department:
        result = await self.session.execute(
            select(Department).where(func.lower(Department.name) == name.strip().lower())
        )
        dept = result.scalar_one_or_none()
        if not dept:
            raise bad_request("UNKNOWN_DEPARTMENT", f"Unknown department '{name}'")
        return dept

    async def spend_by_department(self, month: date) -> dict[int, dict[str, Decimal]]:
        """{department_id: {"approved": x, "pending": y}} for one calendar month."""
        start, end = month_start(month), add_months(month, 1)
        result = await self.session.execute(
            select(Expense.department_id, Expense.status, func.sum(Expense.amount))
            .where(
                Expense.expense_date >= start,
                Expense.expense_date < end,
                Expense.status.in_([ExpenseStatus.APPROVED, ExpenseStatus.PENDING]),
            )
            .group_by(Expense.department_id, Expense.status)
        )
        out: dict[int, dict[str, Decimal]] = {}
        for dept_id, status, total in result.all():
            out.setdefault(dept_id, {"approved": ZERO, "pending": ZERO})[status.value] = Decimal(total or 0)
        return out

    async def list(self, month: date, *, include_unbudgeted: bool = True) -> list[BudgetOut]:
        month = month_start(month)
        depts = (await self.session.execute(select(Department).order_by(Department.name))).scalars().all()
        budgets = {
            b.department_id: b
            for b in (await self.session.execute(select(Budget).where(Budget.month == month))).unique().scalars()
        }
        spend = await self.spend_by_department(month)

        items: list[BudgetOut] = []
        for d in depts:
            b = budgets.get(d.id)
            s = spend.get(d.id, {"approved": ZERO, "pending": ZERO})
            if b is None and not include_unbudgeted:
                continue
            limit = Decimal(b.amount_limit) if b else None
            committed = s["approved"] + s["pending"]
            pct, status = budget_status(limit, committed)
            items.append(BudgetOut(
                id=b.id if b else None,
                department=d.name,
                month=month,
                limit=limit or ZERO,
                spent=s["approved"],
                pending=s["pending"],
                remaining=(limit - committed) if limit is not None else ZERO,
                utilization=round(pct, 1),
                status=status,
            ))
        return items

    async def upsert(self, data: BudgetUpsert) -> BudgetOut:
        dept = await self._department(data.department)
        month = month_start(data.month)
        result = await self.session.execute(
            select(Budget).where(Budget.department_id == dept.id, Budget.month == month)
        )
        budget = result.unique().scalar_one_or_none()
        if budget:
            budget.amount_limit = data.amount_limit
        else:
            self.session.add(Budget(department_id=dept.id, month=month, amount_limit=data.amount_limit))
        await self.session.flush()
        return next(b for b in await self.list(month) if b.department == dept.name)

    async def delete(self, budget_id: int) -> None:
        budget = await self.session.get(Budget, budget_id)
        if not budget:
            raise not_found("Budget")
        await self.session.delete(budget)
        await self.session.flush()

    async def copy(self, req: BudgetCopyRequest) -> dict:
        """Copy every budget from one month to another (e.g. roll last month forward)."""
        src, dst = month_start(req.from_month), month_start(req.to_month)
        if src == dst:
            raise bad_request("SAME_MONTH", "Source and target month must differ")
        source = (await self.session.execute(select(Budget).where(Budget.month == src))).unique().scalars().all()
        if not source:
            raise bad_request("NO_BUDGETS", f"No budgets found for {src:%B %Y}")
        existing = {
            b.department_id: b
            for b in (await self.session.execute(select(Budget).where(Budget.month == dst))).unique().scalars()
        }
        created = updated = skipped = 0
        for b in source:
            target = existing.get(b.department_id)
            if target is None:
                self.session.add(Budget(department_id=b.department_id, month=dst, amount_limit=b.amount_limit))
                created += 1
            elif req.overwrite:
                target.amount_limit = b.amount_limit
                updated += 1
            else:
                skipped += 1
        await self.session.flush()
        return {"created": created, "updated": updated, "skipped": skipped}
