import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ── Organisation ──────────────────────────────────────────────────────────────

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Department name={self.name}>"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Category name={self.name}>"


# ── Auth ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    department = relationship("Department", lazy="joined")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    user_roles = relationship("UserRole", back_populates="role")

    def __repr__(self) -> str:
        return f"<Role name={self.name}>"


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="refresh_tokens")


# ── Expenses ──────────────────────────────────────────────────────────────────

class ExpenseStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        Index("ix_expenses_status_date", "status", "expense_date"),
        Index("ix_expenses_submitter", "submitted_by_id"),
        Index("ix_expenses_department", "department_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant = Column(String(120), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    expense_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(
        Enum(ExpenseStatus, name="expense_status", values_callable=lambda e: [m.value for m in e]),
        default=ExpenseStatus.DRAFT,
        nullable=False,
    )

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    submitted_by_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reviewed_by_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Receipt (stored on disk / object storage; only metadata in the DB)
    receipt_path = Column(String(255), nullable=True)
    receipt_filename = Column(String(255), nullable=True)
    receipt_content_type = Column(String(100), nullable=True)
    receipt_size = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    category = relationship("Category", lazy="joined")
    department = relationship("Department", lazy="joined")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id], lazy="joined")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], lazy="joined")
    events = relationship(
        "ExpenseEvent", back_populates="expense", cascade="all, delete-orphan",
        order_by="ExpenseEvent.created_at",
        passive_deletes=True,     # let ON DELETE CASCADE remove events (no async lazy-load)
    )

    @property
    def reference(self) -> str:
        return f"EXP-{self.id}"

    @property
    def has_receipt(self) -> bool:
        return self.receipt_path is not None


class ExpenseEvent(Base):
    """Append-only audit trail of everything that happens to an expense."""
    __tablename__ = "expense_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(30), nullable=False)          # created, updated, submitted, approved, ...
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    expense = relationship("Expense", back_populates="events")
    actor = relationship("User", lazy="joined")


# ── Budgets ───────────────────────────────────────────────────────────────────

class Budget(Base):
    """Spending limit for one department in one calendar month."""
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("department_id", "month", name="uq_budget_department_month"),
        CheckConstraint("amount_limit >= 0", name="ck_budgets_limit_non_negative"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    month = Column(Date, nullable=False)                  # always the 1st of the month
    amount_limit = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    department = relationship("Department", lazy="joined")


def month_start(d: date) -> date:
    return d.replace(day=1)
