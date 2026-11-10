from typing import Optional

from pydantic import BaseModel, Field

VALID_ROLES = ("EMPLOYEE", "MANAGER", "FINANCE_ADMIN", "SYSTEM_ADMIN")


class UserAdminUpdate(BaseModel):
    """Fields a system admin can change on another account. Omitted fields are left alone."""
    roles: Optional[list[str]] = Field(default=None, min_length=1)
    department: Optional[str] = Field(default=None, description="Department name, or empty string to clear")
    is_active: Optional[bool] = None
