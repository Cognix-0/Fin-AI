"""Finance core: departments, categories, expenses, expense_events, budgets

Revision ID: 002_finance_core
Revises: 001_initial_auth
Create Date: 2026-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_finance_core'
down_revision = '001_initial_auth'
branch_labels = None
depends_on = None

DEPARTMENTS = ['Engineering', 'Sales', 'Marketing', 'Operations']
CATEGORIES = ['Travel', 'Software', 'Meals', 'Office', 'Marketing', 'Utilities']


def upgrade() -> None:
    # ── departments / categories ───────────────────────────────────────────────
    departments = op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
    )
    categories = op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    )
    op.bulk_insert(departments, [{'name': n} for n in DEPARTMENTS])
    op.bulk_insert(categories, [{'name': n, 'is_active': True} for n in CATEGORIES])

    # ── users.department_id ────────────────────────────────────────────────────
    op.add_column(
        'users',
        sa.Column('department_id', sa.Integer(),
                  sa.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True),
    )

    # ── expenses ───────────────────────────────────────────────────────────────
    expense_status = postgresql.ENUM(
        'draft', 'pending', 'approved', 'rejected', name='expense_status', create_type=False,
    )
    expense_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('merchant', sa.String(120), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(3), server_default='USD', nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', expense_status, server_default='draft', nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=False),
        sa.Column('submitted_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewed_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('receipt_path', sa.String(255), nullable=True),
        sa.Column('receipt_filename', sa.String(255), nullable=True),
        sa.Column('receipt_content_type', sa.String(100), nullable=True),
        sa.Column('receipt_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_expenses_amount_positive'),
    )
    op.create_index('ix_expenses_status_date', 'expenses', ['status', 'expense_date'])
    op.create_index('ix_expenses_submitter', 'expenses', ['submitted_by_id'])
    op.create_index('ix_expenses_department', 'expenses', ['department_id'])
    # Human-friendly references (EXP-1001, EXP-1002, ...)
    op.execute("ALTER SEQUENCE expenses_id_seq RESTART WITH 1001")

    # ── expense_events (audit trail) ───────────────────────────────────────────
    op.create_table(
        'expense_events',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('expense_id', sa.Integer(),
                  sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('from_status', sa.String(20), nullable=True),
        sa.Column('to_status', sa.String(20), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_expense_events_expense_id', 'expense_events', ['expense_id'])

    # ── budgets ────────────────────────────────────────────────────────────────
    op.create_table(
        'budgets',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('department_id', sa.Integer(),
                  sa.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('amount_limit', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('department_id', 'month', name='uq_budget_department_month'),
        sa.CheckConstraint('amount_limit >= 0', name='ck_budgets_limit_non_negative'),
    )


def downgrade() -> None:
    op.drop_table('budgets')
    op.drop_index('ix_expense_events_expense_id', table_name='expense_events')
    op.drop_table('expense_events')
    op.drop_table('expenses')
    postgresql.ENUM(name='expense_status').drop(op.get_bind(), checkfirst=True)
    op.drop_column('users', 'department_id')
    op.drop_table('categories')
    op.drop_table('departments')
