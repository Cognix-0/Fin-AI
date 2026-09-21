import re
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
import uuid
from datetime import datetime


# ── Request schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name is required")
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Response schemas ──────────────────────────────────────────────────────────

class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime


# ── Generic API response envelope ─────────────────────────────────────────────

class SuccessResponse(BaseModel):
    success: bool = True
    data: dict | None = None
    message: str | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
