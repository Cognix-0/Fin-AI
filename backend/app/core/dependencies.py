import uuid
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db

security = HTTPBearer(auto_error=False)

APPROVER_ROLES = ("MANAGER", "FINANCE_ADMIN", "SYSTEM_ADMIN")
FINANCE_ROLES = ("FINANCE_ADMIN", "SYSTEM_ADMIN")


def _get_token_from_cookie_or_header(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """Extract JWT from HTTP-only cookie first, then Authorization header."""
    token = request.cookies.get("access_token")
    if token:
        return token
    if credentials:
        return credentials.credentials
    return None


def _unauthorized(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
    )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Validates the JWT and returns the decoded payload (no DB lookup).
    Raises 401 if the token is missing or invalid.
    """
    token = _get_token_from_cookie_or_header(request, credentials)
    if not token:
        raise _unauthorized("NOT_AUTHENTICATED", "Authentication required")
    try:
        return decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("TOKEN_EXPIRED", "Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise _unauthorized("INVALID_TOKEN", "Invalid authentication token")


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated user, loaded fresh from the database for each request."""
    id: uuid.UUID
    email: str
    full_name: str
    roles: tuple[str, ...]
    department_id: Optional[int]

    def has_any(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)

    @property
    def is_approver(self) -> bool:
        return self.has_any(*APPROVER_ROLES)

    @property
    def is_finance(self) -> bool:
        return self.has_any(*FINANCE_ROLES)

    @property
    def is_admin(self) -> bool:
        return "SYSTEM_ADMIN" in self.roles


async def get_current_active_user(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Resolves the token to a live user record. Deactivated or deleted accounts are
    rejected immediately, and role changes apply without waiting for token expiry.
    """
    from app.repositories.user_repository import UserRepository  # avoid import cycle

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise _unauthorized("INVALID_TOKEN", "Invalid authentication token")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise _unauthorized("INVALID_TOKEN", "Account no longer exists")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_INACTIVE", "message": "Your account has been deactivated. Contact support."},
        )
    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=tuple(repo.get_role_names(user)),
        department_id=user.department_id,
    )


def require_role(*roles: str):
    """Factory: creates a dependency that checks the current user has one of the given roles."""
    async def _check(user: CurrentUser = Depends(get_current_active_user)) -> CurrentUser:
        if not user.has_any(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": "You do not have permission to perform this action",
                },
            )
        return user
    return _check


# Convenience shortcuts
require_admin = require_role("SYSTEM_ADMIN")
require_finance_admin = require_role(*FINANCE_ROLES)
require_manager = require_role(*APPROVER_ROLES)
