from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional
from app.core.security import decode_access_token
from app.core.config import settings


security = HTTPBearer(auto_error=False)


def _get_token_from_cookie_or_header(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """Extract JWT from HTTP-only cookie first, then Authorization header."""
    # Prefer cookie (set by login endpoint)
    token = request.cookies.get("access_token")
    if token:
        return token
    # Fallback: Bearer header
    if credentials:
        return credentials.credentials
    return None


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Validates JWT and returns the decoded payload.
    Raises 401 if token is missing or invalid.
    """
    token = _get_token_from_cookie_or_header(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "NOT_AUTHENTICATED", "message": "Authentication required"},
        )
    try:
        payload = decode_access_token(token)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Session expired. Please log in again."},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid authentication token"},
        )


def require_role(*roles: str):
    """Factory: creates a dependency that checks the current user has one of the given roles."""
    def _check(payload: dict = Depends(get_current_user)) -> dict:
        user_roles: list[str] = payload.get("roles", [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": "You do not have permission to perform this action",
                },
            )
        return payload
    return _check


# Convenience shortcuts
require_admin = require_role("SYSTEM_ADMIN")
require_finance_admin = require_role("FINANCE_ADMIN", "SYSTEM_ADMIN")
require_manager = require_role("MANAGER", "FINANCE_ADMIN", "SYSTEM_ADMIN")
