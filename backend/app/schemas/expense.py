from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.models import ExpenseStatus
from app.schemas.common import Money


class ExpenseBase(BaseModel):
    merchant: str = Field(min_length=2, max_length=120)
    amount: Decimal = Field(gt=0, le=Decimal("1000000"), max_digits=12, decimal_places=2)
    expense_date: date
    category: str = Field(min_length=1, max_length=100)
    department: str = Field(min_length=1, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("merchant", "category", "department", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("notes", mode="before")
    @classmethod
    def _blank_notes_to_none(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @field_validator("expense_date")
    @classmethod
    def _not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date cannot be in the future")
        return v


class ExpenseCreate(ExpenseBase):
    submit: bool = False      # true = submit for approval right away, false = save as draft


class ExpenseUpdate(BaseModel):
    merchant: Optional[str] = Field(default=None, min_length=2, max_length=120)
    amount: Optional[Decimal] = Field(default=None, gt=0, le=Decimal("1000000"), max_digits=12, decimal_places=2)
    expense_date: Optional[date] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    department: Optional[str] = Field(default=None, min_length=1, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("merchant", "category", "department", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("notes", mode="before")
    @classmethod
    def _blank_notes_to_none(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @field_validator("expense_date")
    @classmethod
    def _not_in_future(cls, v):
        if v is not None and v > date.today():
            raise ValueError("Date cannot be in the future")
        return v


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class ApproveRequest(BaseModel):
    comment: Optional[str] = Field(default=None, max_length=500)


class BulkDecisionRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)
    action: str = Field(pattern="^(approve|reject)$")
    reason: Optional[str] = Field(default=None, max_length=500)


class ExpenseSort(str, Enum):
    DATE_DESC = "-date"
    DATE_ASC = "date"
    AMOUNT_DESC = "-amount"
    AMOUNT_ASC = "amount"
    CREATED_DESC = "-created"


class ExpenseFilters(BaseModel):
    status: Optional[ExpenseStatus] = None
    category: Optional[str] = None
    department: Optional[str] = None
    search: Optional[str] = Field(default=None, max_length=100)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[Decimal] = Field(default=None, ge=0)
    max_amount: Optional[Decimal] = Field(default=None, ge=0)
    mine: bool = False
    missing_receipt: Optional[bool] = None


class ExpenseOut(BaseModel):
    id: int
    reference: str
    merchant: str
    amount: Money
    currency: str
    expense_date: date
    category: str
    department: str
    notes: Optional[str]
    status: ExpenseStatus
    submitted_by: str
    submitted_by_id: str
    submitted_at: Optional[datetime]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    has_receipt: bool
    receipt_filename: Optional[str]
    created_at: datetime
    updated_at: datetime
    # What the *current viewer* may do — lets the UI hide buttons that would 403
    can_edit: bool = False
    can_review: bool = False

    @classmethod
    def from_model(cls, e, *, can_edit: bool = False, can_review: bool = False) -> "ExpenseOut":
        return cls(
            id=e.id,
            reference=e.reference,
            merchant=e.merchant,
            amount=e.amount,
            currency=e.currency,
            expense_date=e.expense_date,
            category=e.category.name,
            department=e.department.name,
            notes=e.notes,
            status=e.status,
            submitted_by=e.submitted_by.full_name if e.submitted_by else "Unknown",
            submitted_by_id=str(e.submitted_by_id),
            submitted_at=e.submitted_at,
            reviewed_by=e.reviewed_by.full_name if e.reviewed_by else None,
            reviewed_at=e.reviewed_at,
            rejection_reason=e.rejection_reason,
            has_receipt=e.has_receipt,
            receipt_filename=e.receipt_filename,
            created_at=e.created_at,
            updated_at=e.updated_at,
            can_edit=can_edit,
            can_review=can_review,
        )


class ExpenseEventOut(BaseModel):
    action: str
    from_status: Optional[str]
    to_status: Optional[str]
    comment: Optional[str]
    actor: Optional[str]
    created_at: datetime


class BulkDecisionResult(BaseModel):
    succeeded: list[int]
    failed: list[dict]
