"""Initial schema: users, roles, user_roles, refresh_tokens

Revision ID: 001_initial_auth
Revises: 
Create Date: 2026-09-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial_auth'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── roles ──────────────────────────────────────────────────────────────────
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    # ── user_roles ─────────────────────────────────────────────────────────────
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', sa.Integer(),
                  sa.ForeignKey('roles.id'), primary_key=True),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )

    # ── refresh_tokens ─────────────────────────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])

    # ── Seed default roles ─────────────────────────────────────────────────────
    op.execute("""
        INSERT INTO roles (name, description) VALUES
        ('EMPLOYEE',     'Standard employee — can create and submit expenses'),
        ('MANAGER',      'Team manager — can review and approve team expenses'),
        ('FINANCE_ADMIN','Finance administrator — can manage all financial data'),
        ('SYSTEM_ADMIN', 'System administrator — full platform access')
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
