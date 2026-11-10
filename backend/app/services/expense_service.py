"""
Expense workflow.

Lifecycle:   draft ──submit──▶ pending ──approve──▶ approved
               ▲                 │  │
               └───withdraw──────┘  └──reject──▶ rejected ──edit/submit──▶ draft/pending

Visibility:
  * Everyone sees their own expenses (including drafts).
  * MANAGER sees non-draft expenses from their department (or all departments
    if they haven't been assigned one).
  * FINANCE_ADMIN / SYSTEM_ADMIN see all non-draft expenses.

Segregation of duties: nobody can approve or reject their own expense, and a
department-scoped manager can only review expenses for their department.
"""
from __future__ import annotations

import csv
import io
import math
import re
from datetime import datetime, timezone
from typing import Iterable, Optional

from fastapi import UploadFile, status
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.core.errors import AppError, bad_request, conflict, forbidden, not_found
from app.models.models import Category, Department, Expense, ExpenseEvent, ExpenseStatus, User
from app.schemas.expense import (
    BulkDecisionResult, ExpenseCreate, ExpenseEventOut, ExpenseFilters, ExpenseOut,
    ExpenseSort, ExpenseUpdate,
)
from app.services.receipt_storage import ReceiptStorage

EDITABLE = (ExpenseStatus.DRAFT, ExpenseStatus.REJECTED)
EXPORT_LIMIT = 10_000
_REF_RE = re.compile(r"^(?:exp-?)?(\d{1,9})$", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def visibility_clause(user: CurrentUser):
    """SQL condition restricting expenses to what `user` may see."""
    own = Expense.submitted_by_id == user.id
    not_draft = Expense.status != ExpenseStatus.DRAFT
    if user.is_finance:
        return or_(own, not_draft)
    if "MANAGER" in user.roles:
        if user.department_id is None:
            return or_(own, not_draft)
        return or_(own, and_(not_draft, Expense.department_id == user.department_id))
    return own


def can_edit(user: CurrentUser, e: Expense) -> bool:
    return e.submitted_by_id == user.id and e.status in EDITABLE


def can_review(user: CurrentUser, e: Expense) -> bool:
    if e.status != ExpenseStatus.PENDING or not user.is_approver:
        return False
    if e.submitted_by_id == user.id:
        return False
    if user.is_finance or user.department_id is None:
        return True
    return e.department_id == user.department_id


class ExpenseService:
    def __init__(self, session: AsyncSession, storage: Optional[ReceiptStorage] = None):
        self.session = session
        self.storage = storage or ReceiptStorage()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def to_out(self, user: CurrentUser, e: Expense) -> ExpenseOut:
        return ExpenseOut.from_model(e, can_edit=can_edit(user, e), can_review=can_review(user, e))

    async def _category(self, name: str) -> Category:
        result = await self.session.execute(
            select(Category).where(func.lower(Category.name) == name.lower(), Category.is_active.is_(True))
        )
        cat = result.scalar_one_or_none()
        if not cat:
            raise bad_request("UNKNOWN_CATEGORY", f"Unknown category '{name}'")
        return cat

    async def _department(self, name: str) -> Department:
        result = await self.session.execute(
            select(Department).where(func.lower(Department.name) == name.lower())
        )
        dept = result.scalar_one_or_none()
        if not dept:
            raise bad_request("UNKNOWN_DEPARTMENT", f"Unknown department '{name}'")
        return dept

    def _log(self, e: Expense, actor: CurrentUser, action: str,
             from_status: Optional[ExpenseStatus] = None, comment: Optional[str] = None) -> None:
        self.session.add(ExpenseEvent(
            expense_id=e.id,
            actor_id=actor.id,
            action=action,
            from_status=from_status.value if from_status else None,
            to_status=e.status.value if e.status else None,
            comment=comment,
        ))

    async def _get_visible(self, expense_id: int, user: CurrentUser, *, lock: bool = False) -> Expense:
        stmt = select(Expense).where(Expense.id == expense_id, visibility_clause(user))
        if lock:
            # Serialise concurrent transitions (e.g. two managers approving at once)
            stmt = stmt.with_for_update(of=Expense)
        result = await self.session.execute(stmt)
        e = result.unique().scalar_one_or_none()
        if not e:
            raise not_found("Expense")
        return e

    async def _reload(self, e: Expense) -> Expense:
        await self.session.flush()
        await self.session.refresh(e)
        return e

    # ── Queries ───────────────────────────────────────────────────────────────

    def _filtered(self, stmt: Select, f: ExpenseFilters, user: CurrentUser) -> Select:
        stmt = stmt.where(visibility_clause(user))
        if f.mine:
            stmt = stmt.where(Expense.submitted_by_id == user.id)
        if f.status:
            stmt = stmt.where(Expense.status == f.status)
        if f.category:
            stmt = stmt.where(Expense.category.has(func.lower(Category.name) == f.category.lower()))
        if f.department:
            stmt = stmt.where(Expense.department.has(func.lower(Department.name) == f.department.lower()))
        if f.date_from:
            stmt = stmt.where(Expense.expense_date >= f.date_from)
        if f.date_to:
            stmt = stmt.where(Expense.expense_date <= f.date_to)
        if f.min_amount is not None:
            stmt = stmt.where(Expense.amount >= f.min_amount)
        if f.max_amount is not None:
            stmt = stmt.where(Expense.amount <= f.max_amount)
        if f.missing_receipt is True:
            stmt = stmt.where(Expense.receipt_path.is_(None))
        elif f.missing_receipt is False:
            stmt = stmt.where(Expense.receipt_path.is_not(None))
        if f.search and (q := f.search.strip()):
            like = f"%{q}%"
            conds = [
                Expense.merchant.ilike(like),
                Expense.submitted_by.has(User.full_name.ilike(like)),
                Expense.department.has(Department.name.ilike(like)),
            ]
            if m := _REF_RE.match(q):
                conds.append(Expense.id == int(m.group(1)))
            stmt = stmt.where(or_(*conds))
        return stmt

    @staticmethod
    def _order(stmt: Select, sort: ExpenseSort) -> Select:
        order = {
            ExpenseSort.DATE_DESC: (Expense.expense_date.desc(), Expense.id.desc()),
            ExpenseSort.DATE_ASC: (Expense.expense_date.asc(), Expense.id.asc()),
            ExpenseSort.AMOUNT_DESC: (Expense.amount.desc(), Expense.id.desc()),
            ExpenseSort.AMOUNT_ASC: (Expense.amount.asc(), Expense.id.asc()),
            ExpenseSort.CREATED_DESC: (Expense.created_at.desc(), Expense.id.desc()),
        }[sort]
        return stmt.order_by(*order)

    async def list(
        self, user: CurrentUser, filters: ExpenseFilters, *,
        page: int = 1, page_size: int = 20, sort: ExpenseSort = ExpenseSort.DATE_DESC,
    ) -> dict:
        count_stmt = self._filtered(select(func.count(Expense.id)), filters, user)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = self._order(self._filtered(select(Expense), filters, user), sort)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).unique().scalars().all()

        return {
            "items": [self.to_out(user, e).model_dump(mode="json") for e in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, math.ceil(total / page_size)),
        }

    async def get(self, expense_id: int, user: CurrentUser) -> ExpenseOut:
        return self.to_out(user, await self._get_visible(expense_id, user))

    async def history(self, expense_id: int, user: CurrentUser) -> list[ExpenseEventOut]:
        await self._get_visible(expense_id, user)
        result = await self.session.execute(
            select(ExpenseEvent)
            .where(ExpenseEvent.expense_id == expense_id)
            .order_by(ExpenseEvent.created_at, ExpenseEvent.id)
        )
        return [
            ExpenseEventOut(
                action=ev.action,
                from_status=ev.from_status,
                to_status=ev.to_status,
                comment=ev.comment,
                actor=ev.actor.full_name if ev.actor else None,
                created_at=ev.created_at,
            )
            for ev in result.unique().scalars()
        ]

    async def export_csv(self, user: CurrentUser, filters: ExpenseFilters, sort: ExpenseSort) -> str:
        stmt = self._order(self._filtered(select(Expense), filters, user), sort).limit(EXPORT_LIMIT)
        rows: Iterable[Expense] = (await self.session.execute(stmt)).unique().scalars()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Reference", "Date", "Merchant", "Category", "Department", "Submitted by",
            "Amount", "Currency", "Status", "Receipt", "Reviewed by", "Rejection reason", "Notes",
        ])
        for e in rows:
            writer.writerow([_csv_safe(v) for v in (
                e.reference, e.expense_date.isoformat(), e.merchant, e.category.name, e.department.name,
                e.submitted_by.full_name if e.submitted_by else "", f"{e.amount:.2f}", e.currency,
                e.status.value, "yes" if e.has_receipt else "no",
                e.reviewed_by.full_name if e.reviewed_by else "", e.rejection_reason or "", e.notes or "",
            )])
        return buf.getvalue()

    # ── Commands ──────────────────────────────────────────────────────────────

    async def create(self, data: ExpenseCreate, user: CurrentUser) -> ExpenseOut:
        category = await self._category(data.category)
        department = await self._department(data.department)
        e = Expense(
            merchant=data.merchant,
            amount=data.amount,
            expense_date=data.expense_date,
            notes=data.notes,
            category_id=category.id,
            department_id=department.id,
            submitted_by_id=user.id,
            status=ExpenseStatus.PENDING if data.submit else ExpenseStatus.DRAFT,
            submitted_at=_now() if data.submit else None,
        )
        self.session.add(e)
        await self.session.flush()
        self._log(e, user, "submitted" if data.submit else "created")
        return self.to_out(user, await self._reload(e))

    async def update(self, expense_id: int, data: ExpenseUpdate, user: CurrentUser) -> ExpenseOut:
        e = await self._get_visible(expense_id, user, lock=True)
        if not can_edit(user, e):
            raise self._cannot("edit", e, user)

        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return self.to_out(user, e)
        if "category" in changes:
            e.category_id = (await self._category(changes.pop("category"))).id
        if "department" in changes:
            e.department_id = (await self._department(changes.pop("department"))).id
        for field, value in changes.items():
            if field in ("merchant", "amount", "expense_date") and value is None:
                raise bad_request("INVALID_FIELD", f"{field} cannot be empty")
            setattr(e, field, value)

        previous = e.status
        if e.status == ExpenseStatus.REJECTED:
            # Editing a rejected expense puts it back into draft for resubmission
            e.status = ExpenseStatus.DRAFT
            e.rejection_reason = None
        self._log(e, user, "updated", previous)
        return self.to_out(user, await self._reload(e))

    async def delete(self, expense_id: int, user: CurrentUser) -> None:
        e = await self._get_visible(expense_id, user, lock=True)
        if e.submitted_by_id != user.id or e.status not in EDITABLE:
            raise self._cannot("delete", e, user)
        receipt = e.receipt_path
        await self.session.delete(e)
        await self.session.flush()
        self.storage.delete(receipt)

    async def submit(self, expense_id: int, user: CurrentUser) -> ExpenseOut:
        e = await self._get_visible(expense_id, user, lock=True)
        if not can_edit(user, e):
            raise self._cannot("submit", e, user)
        previous = e.status
        e.status = ExpenseStatus.PENDING
        e.submitted_at = _now()
        e.rejection_reason = None
        e.reviewed_by_id = None
        e.reviewed_at = None
        self._log(e, user, "submitted", previous)
        return self.to_out(user, await self._reload(e))

    async def withdraw(self, expense_id: int, user: CurrentUser) -> ExpenseOut:
        e = await self._get_visible(expense_id, user, lock=True)
        if e.submitted_by_id != user.id or e.status != ExpenseStatus.PENDING:
            raise self._cannot("withdraw", e, user)
        e.status = ExpenseStatus.DRAFT
        e.submitted_at = None
        self._log(e, user, "withdrawn", ExpenseStatus.PENDING)
        return self.to_out(user, await self._reload(e))

    async def approve(self, expense_id: int, user: CurrentUser, comment: Optional[str] = None) -> ExpenseOut:
        e = await self._get_visible(expense_id, user, lock=True)
        self._check_review(user, e)
        e.status = ExpenseStatus.APPROVED
        e.reviewed_by_id = user.id
        e.reviewed_at = _now()
        e.rejection_reason = None
        self._log(e, user, "approved", ExpenseStatus.PENDING, comment)
        return self.to_out(user, await self._reload(e))

    async def reject(self, expense_id: int, user: CurrentUser, reason: str) -> ExpenseOut:
        e = await self._get_visible(expense_id, user, lock=True)
        self._check_review(user, e)
        e.status = ExpenseStatus.REJECTED
        e.reviewed_by_id = user.id
        e.reviewed_at = _now()
        e.rejection_reason = reason
        self._log(e, user, "rejected", ExpenseStatus.PENDING, reason)
        return self.to_out(user, await self._reload(e))

    async def bulk_decide(
        self, ids: list[int], action: str, user: CurrentUser, reason: Optional[str],
    ) -> BulkDecisionResult:
        if action == "reject" and not (reason and len(reason.strip()) >= 3):
            raise bad_request("REASON_REQUIRED", "A rejection reason of at least 3 characters is required")
        succeeded, failed = [], []
        for expense_id in dict.fromkeys(ids):          # de-duplicate, keep order
            try:
                async with self.session.begin_nested():   # one bad item doesn't undo the rest
                    if action == "approve":
                        await self.approve(expense_id, user)
                    else:
                        await self.reject(expense_id, user, reason.strip())
                succeeded.append(expense_id)
            except AppError as exc:
                failed.append({"id": expense_id, **exc.detail})
        return BulkDecisionResult(succeeded=succeeded, failed=failed)

    async def attach_receipt(self, expense_id: int, upload: UploadFile, user: CurrentUser) -> ExpenseOut:
        e = await self._get_visible(expense_id, user, lock=True)
        if e.submitted_by_id != user.id or e.status == ExpenseStatus.APPROVED:
            raise self._cannot("attach a receipt to", e, user)
        meta = await self.storage.save(upload)
        old = e.receipt_path
        for k, v in meta.items():
            setattr(e, k, v)
        self._log(e, user, "receipt_replaced" if old else "receipt_added", e.status, meta["receipt_filename"])
        out = self.to_out(user, await self._reload(e))
        self.storage.delete(old)
        return out

    async def remove_receipt(self, expense_id: int, user: CurrentUser) -> ExpenseOut:
        e = await self._get_visible(expense_id, user, lock=True)
        if e.submitted_by_id != user.id or e.status not in EDITABLE:
            raise self._cannot("remove the receipt from", e, user)
        if not e.receipt_path:
            raise not_found("Receipt")
        old = e.receipt_path
        e.receipt_path = e.receipt_filename = e.receipt_content_type = None
        e.receipt_size = None
        self._log(e, user, "receipt_removed", e.status)
        out = self.to_out(user, await self._reload(e))
        self.storage.delete(old)
        return out

    async def receipt_file(self, expense_id: int, user: CurrentUser) -> tuple[str, str, str]:
        """Returns (absolute path, content type, download filename)."""
        e = await self._get_visible(expense_id, user)
        if not e.receipt_path:
            raise not_found("Receipt")
        path = self.storage.resolve(e.receipt_path)
        if not path.is_file():
            raise not_found("Receipt")
        return str(path), e.receipt_content_type or "application/octet-stream", e.receipt_filename or path.name

    # ── Errors ────────────────────────────────────────────────────────────────

    def _check_review(self, user: CurrentUser, e: Expense) -> None:
        if not user.is_approver:
            raise forbidden("Only managers and finance admins can review expenses")
        if e.submitted_by_id == user.id:
            raise forbidden("You cannot review your own expense")
        if e.status != ExpenseStatus.PENDING:
            raise conflict("INVALID_STATUS", f"{e.reference} is {e.status.value}, not pending")
        if not can_review(user, e):
            raise forbidden("You can only review expenses for your own department")

    @staticmethod
    def _cannot(verb: str, e: Expense, user: CurrentUser) -> AppError:
        if e.submitted_by_id != user.id:
            return forbidden(f"Only the submitter can {verb} this expense")
        return AppError(
            status.HTTP_409_CONFLICT, "INVALID_STATUS",
            f"You can't {verb} {e.reference} while it is {e.status.value}",
        )


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection (=, +, -, @ at the start of a cell)."""
    s = str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r") and not _is_number(s):
        return "'" + s
    return s


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False
