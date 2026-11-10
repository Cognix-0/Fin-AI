from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_active_user, require_manager
from app.db.session import get_db
from app.models.models import ExpenseStatus
from app.schemas.common import ok
from app.schemas.expense import (
    ApproveRequest, BulkDecisionRequest, ExpenseCreate, ExpenseFilters, ExpenseSort,
    ExpenseUpdate, RejectRequest,
)
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def get_filters(
    status: Optional[ExpenseStatus] = None,
    category: Optional[str] = Query(None, max_length=100),
    department: Optional[str] = Query(None, max_length=100),
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    min_amount: Optional[Decimal] = Query(None, ge=0),
    max_amount: Optional[Decimal] = Query(None, ge=0),
    mine: bool = False,
    missing_receipt: Optional[bool] = None,
) -> ExpenseFilters:
    return ExpenseFilters(
        status=status, category=category, department=department, search=search,
        date_from=date_from, date_to=date_to, min_amount=min_amount, max_amount=max_amount,
        mine=mine, missing_receipt=missing_receipt,
    )


@router.get("")
async def list_expenses(
    filters: ExpenseFilters = Depends(get_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: ExpenseSort = ExpenseSort.DATE_DESC,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List expenses visible to the caller, with filters, search, sorting and pagination."""
    return ok(await ExpenseService(db).list(user, filters, page=page, page_size=page_size, sort=sort))


@router.get("/export")
async def export_expenses(
    filters: ExpenseFilters = Depends(get_filters),
    sort: ExpenseSort = ExpenseSort.DATE_DESC,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the filtered expense list as CSV (max 10,000 rows)."""
    csv_text = await ExpenseService(db).export_csv(user, filters, sort)
    filename = f"expenses-{date.today().isoformat()}.csv"
    return Response(
        content="﻿" + csv_text,          # BOM so Excel detects UTF-8
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/bulk-decision")
async def bulk_decision(
    data: BulkDecisionRequest,
    user: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject several pending expenses at once. Reports per-item failures."""
    result = await ExpenseService(db).bulk_decide(data.ids, data.action, user, data.reason)
    return ok(result.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreate,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an expense as a draft, or submit it straight away with `submit: true`."""
    expense = await ExpenseService(db).create(data, user)
    return ok({"expense": expense.model_dump(mode="json")})


@router.get("/{expense_id}")
async def get_expense(
    expense_id: int,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    expense = await ExpenseService(db).get(expense_id, user)
    return ok({"expense": expense.model_dump(mode="json")})


@router.patch("/{expense_id}")
async def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit your own draft or rejected expense. Editing a rejected expense returns it to draft."""
    expense = await ExpenseService(db).update(expense_id, data, user)
    return ok({"expense": expense.model_dump(mode="json")})


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete your own draft or rejected expense."""
    await ExpenseService(db).delete(expense_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{expense_id}/history")
async def expense_history(
    expense_id: int,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Audit trail: who did what to this expense and when."""
    events = await ExpenseService(db).history(expense_id, user)
    return ok({"events": [e.model_dump(mode="json") for e in events]})


@router.post("/{expense_id}/submit")
async def submit_expense(
    expense_id: int,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    expense = await ExpenseService(db).submit(expense_id, user)
    return ok({"expense": expense.model_dump(mode="json")})


@router.post("/{expense_id}/withdraw")
async def withdraw_expense(
    expense_id: int,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Pull a pending expense back to draft before it's reviewed."""
    expense = await ExpenseService(db).withdraw(expense_id, user)
    return ok({"expense": expense.model_dump(mode="json")})


@router.post("/{expense_id}/approve")
async def approve_expense(
    expense_id: int,
    data: Optional[ApproveRequest] = None,
    user: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    expense = await ExpenseService(db).approve(expense_id, user, data.comment if data else None)
    return ok({"expense": expense.model_dump(mode="json")})


@router.post("/{expense_id}/reject")
async def reject_expense(
    expense_id: int,
    data: RejectRequest,
    user: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    expense = await ExpenseService(db).reject(expense_id, user, data.reason)
    return ok({"expense": expense.model_dump(mode="json")})


@router.post("/{expense_id}/receipt")
async def upload_receipt(
    expense_id: int,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach or replace a receipt (PNG, JPG, WebP or PDF, max 10 MB)."""
    expense = await ExpenseService(db).attach_receipt(expense_id, file, user)
    return ok({"expense": expense.model_dump(mode="json")})


@router.get("/{expense_id}/receipt")
async def download_receipt(
    expense_id: int,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    path, content_type, filename = await ExpenseService(db).receipt_file(expense_id, user)
    return FileResponse(
        path,
        media_type=content_type,
        filename=filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.delete("/{expense_id}/receipt")
async def delete_receipt(
    expense_id: int,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    expense = await ExpenseService(db).remove_receipt(expense_id, user)
    return ok({"expense": expense.model_dump(mode="json")})
