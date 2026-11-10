"""
Dashboard analytics and rule-based spending insights.

All figures count "committed" spend: approved + pending expenses. Drafts and
rejected expenses are excluded. Results respect the caller's visibility:
finance roles see the whole company, department managers see their department,
everyone else sees their own expenses.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.models.models import Category, Department, Expense, ExpenseStatus
from app.services.budget_service import BudgetService
from app.services.dates import add_months, month_start, period_bounds
from app.services.expense_service import visibility_clause

COMMITTED = (ExpenseStatus.APPROVED, ExpenseStatus.PENDING)
STALE_DAYS = 7
TREND_MIN_AMOUNT = Decimal("500")
TREND_MIN_CHANGE = 20.0
OUTLIER_FACTOR = 3
MAX_INSIGHTS = 6
ZERO = Decimal("0")


def _money(v: Decimal | float) -> str:
    return f"${Decimal(v):,.2f}".replace(".00", "")


def _pct_change(current: Decimal, previous: Decimal) -> float | None:
    if previous == 0:
        return None
    return round(float((current - previous) / previous * 100), 1)


def scope_of(user: CurrentUser) -> str:
    if user.is_finance:
        return "company"
    if "MANAGER" in user.roles:
        return "department" if user.department_id else "company"
    return "personal"


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _base(self, user: CurrentUser, *cols):
        return select(*cols).where(visibility_clause(user), Expense.status.in_(COMMITTED))

    async def _total(self, user: CurrentUser, start: date, end: date) -> tuple[Decimal, int]:
        row = (await self.session.execute(
            self._base(user, func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id))
            .where(Expense.expense_date.between(start, end))
        )).one()
        return Decimal(row[0] or 0), int(row[1])

    async def _by_category(self, user: CurrentUser, start: date, end: date) -> dict[str, Decimal]:
        rows = await self.session.execute(
            self._base(user, Category.name, func.sum(Expense.amount))
            .join(Category, Category.id == Expense.category_id)
            .where(Expense.expense_date.between(start, end))
            .group_by(Category.name)
        )
        return {name: Decimal(total or 0) for name, total in rows.all()}

    async def summary(self, user: CurrentUser, period: str, today: date | None = None) -> dict:
        today = today or date.today()
        start, end, prev_start, prev_end = period_bounds(period, today)

        total, count = await self._total(user, start, end)
        prev_total, _ = await self._total(user, prev_start, prev_end)

        # Pending queue (all dates)
        pending_row = (await self.session.execute(
            select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0))
            .where(visibility_clause(user), Expense.status == ExpenseStatus.PENDING)
        )).one()

        missing_receipts = (await self.session.execute(
            self._base(user, func.count(Expense.id)).where(Expense.receipt_path.is_(None))
        )).scalar_one()

        # Monthly series: last 12 calendar months including the current one
        first_month = add_months(today, -11)
        y, m = extract("year", Expense.expense_date), extract("month", Expense.expense_date)
        monthly_rows = await self.session.execute(
            self._base(user, y, m, func.sum(Expense.amount))
            .where(Expense.expense_date >= first_month, Expense.expense_date <= today)
            .group_by(y, m)
        )
        by_month = {(int(r[0]), int(r[1])): Decimal(r[2] or 0) for r in monthly_rows.all()}
        monthly = []
        for i in range(12):
            d = add_months(first_month, i)
            monthly.append({
                "month": d.isoformat()[:7],
                "label": d.strftime("%b"),
                "amount": float(by_month.get((d.year, d.month), ZERO)),
            })

        categories = await self._by_category(user, start, end)
        cat_total = sum(categories.values(), ZERO)
        by_category = [
            {"category": k, "amount": float(v),
             "share": round(float(v / cat_total * 100), 1) if cat_total else 0.0}
            for k, v in sorted(categories.items(), key=lambda kv: kv[1], reverse=True)
        ]

        dept_rows = await self.session.execute(
            self._base(user, Department.name, func.sum(Expense.amount))
            .join(Department, Department.id == Expense.department_id)
            .where(Expense.expense_date.between(start, end))
            .group_by(Department.name)
            .order_by(func.sum(Expense.amount).desc())
        )
        by_department = [{"department": n, "amount": float(a or 0)} for n, a in dept_rows.all()]

        merchant_rows = await self.session.execute(
            self._base(user, Expense.merchant, func.sum(Expense.amount), func.count(Expense.id))
            .where(Expense.expense_date.between(start, end))
            .group_by(Expense.merchant)
            .order_by(func.sum(Expense.amount).desc())
            .limit(5)
        )
        top_merchants = [
            {"merchant": n, "amount": float(a or 0), "count": int(c)} for n, a, c in merchant_rows.all()
        ]

        # Budgets are organisation-wide figures for the current month
        budgets = await BudgetService(self.session).list(today, include_unbudgeted=False)
        budget_limit = sum((b.limit for b in budgets), ZERO)
        budget_committed = sum((b.spent + b.pending for b in budgets), ZERO)

        return {
            "period": period,
            "scope": scope_of(user),
            "range": {"start": start.isoformat(), "end": end.isoformat()},
            "kpis": {
                "total_spend": float(total),
                "previous_spend": float(prev_total),
                "change_pct": _pct_change(total, prev_total),
                "expense_count": count,
                "average_expense": float(total / count) if count else 0.0,
                "pending_count": int(pending_row[0]),
                "pending_total": float(pending_row[1] or 0),
                "missing_receipts": int(missing_receipts),
                "budget_limit": float(budget_limit),
                "budget_committed": float(budget_committed),
                "budget_utilization": round(float(budget_committed / budget_limit * 100), 1) if budget_limit else None,
            },
            "monthly": monthly,
            "by_category": by_category,
            "by_department": by_department,
            "top_merchants": top_merchants,
            "insights": await self.insights(user, today),
        }

    # ── Insights ──────────────────────────────────────────────────────────────

    async def insights(self, user: CurrentUser, today: date | None = None) -> list[dict]:
        today = today or date.today()
        out: list[dict] = []

        # 1. Budget pressure (company/department scopes only)
        if scope_of(user) != "personal":
            for b in await BudgetService(self.session).list(today, include_unbudgeted=False):
                if user.department_id and not user.is_finance and scope_of(user) == "department":
                    # Department managers only hear about their own budget
                    dept_id = (await self.session.execute(
                        select(Department.id).where(Department.name == b.department)
                    )).scalar_one()
                    if dept_id != user.department_id:
                        continue
                committed = b.spent + b.pending
                if b.status == "over_budget":
                    over = b.utilization - 100
                    extra = f", including {_money(b.pending)} awaiting approval" if b.pending else ""
                    out.append(_insight("warning", "budget",
                        f"{b.department} is {over:.1f}% over its {today:%B} budget "
                        f"({_money(committed)} of {_money(b.limit)}{extra})."))
                elif b.status == "near_limit":
                    out.append(_insight("warning", "budget",
                        f"{b.department} has used {b.utilization:.0f}% of its {today:%B} budget "
                        f"with {_money(b.remaining)} left."))

        # 2. Pending expenses without receipts
        rows = (await self.session.execute(
            select(Expense.id, Expense.amount)
            .where(visibility_clause(user), Expense.status == ExpenseStatus.PENDING,
                   Expense.receipt_path.is_(None))
            .order_by(Expense.amount.desc())
        )).all()
        if len(rows) == 1:
            out.append(_insight("warning", "receipts",
                f"EXP-{rows[0][0]} ({_money(rows[0][1])}) has no receipt attached — "
                "ask the submitter to upload one before approval.", expense_id=rows[0][0]))
        elif rows:
            out.append(_insight("warning", "receipts",
                f"{len(rows)} pending expenses have no receipt attached, totalling "
                f"{_money(sum(Decimal(r[1]) for r in rows))}."))

        # 3. Stale approvals
        cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
        stale = (await self.session.execute(
            select(func.count(Expense.id))
            .where(visibility_clause(user), Expense.status == ExpenseStatus.PENDING,
                   Expense.submitted_at.is_not(None), Expense.submitted_at < cutoff)
        )).scalar_one()
        if stale:
            noun = "expense has" if stale == 1 else "expenses have"
            out.append(_insight("warning", "approvals",
                f"{stale} {noun} been waiting more than {STALE_DAYS} days for approval."))

        # 4. Possible duplicates: same submitter, merchant, amount and date
        dupes = (await self.session.execute(
            select(Expense.merchant, Expense.amount, Expense.expense_date, func.count(Expense.id))
            .where(visibility_clause(user),
                   Expense.status.in_(COMMITTED + (ExpenseStatus.DRAFT,)))
            .group_by(Expense.submitted_by_id, Expense.merchant, Expense.amount, Expense.expense_date)
            .having(func.count(Expense.id) > 1)
            .limit(3)
        )).all()
        for merchant, amount, d, n in dupes:
            out.append(_insight("warning", "duplicates",
                f"Possible duplicate: {n} expenses of {_money(amount)} at {merchant} on {d:%b %d} "
                "from the same person."))

        # 5. Outliers in the approval queue
        avg = (await self.session.execute(
            select(func.avg(Expense.amount))
            .where(visibility_clause(user), Expense.status == ExpenseStatus.APPROVED)
        )).scalar_one()
        if avg:
            threshold = Decimal(avg) * OUTLIER_FACTOR
            big = (await self.session.execute(
                select(Expense.id, Expense.amount, Expense.merchant)
                .where(visibility_clause(user), Expense.status == ExpenseStatus.PENDING,
                       Expense.amount > threshold)
                .order_by(Expense.amount.desc())
                .limit(2)
            )).all()
            for eid, amount, merchant in big:
                out.append(_insight("info", "outlier",
                    f"EXP-{eid} ({merchant}, {_money(amount)}) is {Decimal(amount) / Decimal(avg):.1f}× "
                    "the average approved expense — worth a closer look.", expense_id=eid))

        # 6. Category trends: last 30 days vs the 30 before
        start, end, prev_start, prev_end = period_bounds("30d", today)
        current = await self._by_category(user, start, end)
        previous = await self._by_category(user, prev_start, prev_end)
        trends = []
        for cat, amount in current.items():
            change = _pct_change(amount, previous.get(cat, ZERO))
            if change is not None and abs(change) >= TREND_MIN_CHANGE and max(amount, previous[cat]) >= TREND_MIN_AMOUNT:
                trends.append((abs(change), cat, change))
        for _, cat, change in sorted(trends, reverse=True)[:2]:
            direction = "up" if change > 0 else "down"
            out.append(_insight("info", "trend",
                f"{cat} spend is {direction} {abs(change):.0f}% vs the previous 30 days."))

        if not out:
            out.append(_insight("info", "all_clear",
                "No budget overruns, missing receipts or unusual spending detected."))

        # Warnings first, then info; cap the list
        out.sort(key=lambda i: 0 if i["tone"] == "warning" else 1)
        return out[:MAX_INSIGHTS]


def _insight(tone: str, kind: str, text: str, **extra) -> dict:
    return {"tone": tone, "kind": kind, "text": text, **extra}
