from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie config
COOKIE_MAX_AGE = settings.jwt_expire_minutes * 60   # seconds
COOKIE_SECURE = settings.is_production              # HTTPS only in prod
COOKIE_SAMESITE = "lax"


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user. Returns user info and sets an auth cookie."""
    service = AuthService(db)
    user = await service.register(data)

    # Auto-login after registration
    _, token = await service.login(
        LoginRequest(email=data.email, password=data.password)
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=COOKIE_MAX_AGE,
    )

    return {
        "success": True,
        "data": {
            "user": user.model_dump(mode="json"),
            "message": "Account created successfully",
        },
    }


@router.post("/login", response_model=dict)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user. Sets an HTTP-only JWT cookie on success."""
    service = AuthService(db)
    user, token = await service.login(data)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=COOKIE_MAX_AGE,
    )

    return {
        "success": True,
        "data": {
            "user": user.model_dump(mode="json"),
        },
    }


@router.post("/logout")
async def logout(response: Response):
    """Clear the auth cookie to log out."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=dict)
async def get_me(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user's profile."""
    service = AuthService(db)
    user = await service.get_me(payload["sub"])
    return {"success": True, "data": {"user": user.model_dump(mode="json")}}
