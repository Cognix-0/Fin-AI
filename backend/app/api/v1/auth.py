from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import CurrentUser, get_current_active_user, get_current_user
from app.core.rate_limit import login_limiter
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest, LoginRequest, RegisterRequest, UpdateProfileRequest,
)
from app.schemas.common import ok
from app.services.auth_service import AuthService, TokenPair

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie config
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
COOKIE_SECURE = settings.is_production              # HTTPS only in prod
COOKIE_SAMESITE = "lax"


def _set_auth_cookies(response: Response, tokens: TokenPair) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=tokens.access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    # Path "/" (not just /auth) so the Next.js middleware can see the user still
    # has a session after the short-lived access cookie expires.
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=settings.jwt_refresh_expire_days * 24 * 3600,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    for key in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(
            key=key, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, path="/",
        )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user. Returns user info and signs them in."""
    user, tokens = await AuthService(db).register(data)
    _set_auth_cookies(response, tokens)
    return ok({"user": user.model_dump(mode="json"), "message": "Account created successfully"})


@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user. Sets HTTP-only access + refresh cookies on success."""
    key = f"{_client_ip(request)}|{data.email.lower()}"
    login_limiter.check(key)
    try:
        user, tokens = await AuthService(db).login(data)
    except HTTPException as exc:
        if isinstance(exc.detail, dict) and exc.detail.get("code") == "INVALID_CREDENTIALS":
            login_limiter.record_failure(key)
        raise
    login_limiter.reset(key)
    _set_auth_cookies(response, tokens)
    return ok({"user": user.model_dump(mode="json")})


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Exchange the refresh cookie for a new access + refresh token pair (rotation)."""
    try:
        user, tokens = await AuthService(db).refresh(request.cookies.get(REFRESH_COOKIE))
    except HTTPException as exc:
        # Return directly (not raise) so the cookie-clearing headers survive
        failed = JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})
        _clear_auth_cookies(failed)
        return failed
    _set_auth_cookies(response, tokens)
    return ok({"user": user.model_dump(mode="json")})


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the refresh token and clear auth cookies."""
    await AuthService(db).logout(request.cookies.get(REFRESH_COOKIE))
    _clear_auth_cookies(response)
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_me(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user's profile."""
    user = await AuthService(db).get_me(payload["sub"])
    return ok({"user": user.model_dump(mode="json")})


@router.patch("/me")
async def update_me(
    data: UpdateProfileRequest,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the signed-in user's own profile."""
    updated = await AuthService(db).update_profile(user.id, data)
    return ok({"user": updated.model_dump(mode="json")})


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password. Signs out all other sessions."""
    updated, tokens = await AuthService(db).change_password(user.id, data)
    _set_auth_cookies(response, tokens)
    return ok({"user": updated.model_dump(mode="json")}, message="Password changed")
