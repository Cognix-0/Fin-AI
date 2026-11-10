import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    burn_password_check, create_access_token, generate_refresh_token, hash_password,
    hash_refresh_token, refresh_token_expiry, verify_password,
)
from app.models.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest, LoginRequest, RegisterRequest, UpdateProfileRequest, UserResponse,
)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


def _as_utc(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; Postgres returns aware ones
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
    )


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_REFRESH_TOKEN", "message": "Session expired. Please log in again."},
    )


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)

    def to_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=self.repo.get_role_names(user),
            department=user.department.name if user.department else None,
            created_at=user.created_at,
        )

    async def _issue_tokens(self, user: User) -> TokenPair:
        access = create_access_token(subject=str(user.id), roles=self.repo.get_role_names(user))
        refresh = generate_refresh_token()
        await self.repo.purge_expired_refresh_tokens(user.id)
        await self.repo.add_refresh_token(user.id, hash_refresh_token(refresh), refresh_token_expiry())
        return TokenPair(access, refresh)

    async def _load(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            )
        return user

    async def register(self, data: RegisterRequest) -> tuple[UserResponse, TokenPair]:
        """
        Register a new user with the EMPLOYEE role and sign them in.
        """
        if await self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_TAKEN", "message": "An account with this email already exists"},
            )

        user = await self.repo.create(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        # All new users get EMPLOYEE role — never ADMIN
        await self.repo.assign_role(user, "EMPLOYEE")
        await self.session.flush()
        user_id = user.id
        self.session.expire(user)            # reload with roles + department populated
        user = await self._load(user_id)
        return self.to_response(user), await self._issue_tokens(user)

    async def login(self, data: LoginRequest) -> tuple[UserResponse, TokenPair]:
        user = await self.repo.get_by_email(data.email)
        if not user:
            # Spend the same time as a real check so timing doesn't leak which emails exist
            burn_password_check(data.password)
            raise _invalid_credentials()
        if not verify_password(data.password, user.password_hash):
            raise _invalid_credentials()
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCOUNT_INACTIVE", "message": "Your account has been deactivated. Contact support."},
            )
        return self.to_response(user), await self._issue_tokens(user)

    async def refresh(self, refresh_token: Optional[str]) -> tuple[UserResponse, TokenPair]:
        """
        Rotate a refresh token: the presented token is revoked and a new pair issued.
        Presenting an already-revoked token means it was stolen and replayed, so
        every session for that user is revoked.
        """
        if not refresh_token:
            raise _invalid_refresh()
        stored = await self.repo.get_refresh_token(hash_refresh_token(refresh_token))
        if not stored:
            raise _invalid_refresh()
        if stored.revoked:
            await self.repo.revoke_all_refresh_tokens(stored.user_id)
            await self.session.commit()      # keep the revocation even though we raise
            raise _invalid_refresh()
        if _as_utc(stored.expires_at) <= datetime.now(timezone.utc):
            raise _invalid_refresh()

        user = await self._load(stored.user_id)
        if not user.is_active:
            raise _invalid_refresh()
        stored.revoked = True
        return self.to_response(user), await self._issue_tokens(user)

    async def logout(self, refresh_token: Optional[str]) -> None:
        if not refresh_token:
            return
        stored = await self.repo.get_refresh_token(hash_refresh_token(refresh_token))
        if stored:
            stored.revoked = True

    async def get_me(self, user_id: str) -> UserResponse:
        """Return the currently authenticated user's profile."""
        return self.to_response(await self._load(uuid.UUID(user_id)))

    async def update_profile(self, user_id: uuid.UUID, data: UpdateProfileRequest) -> UserResponse:
        user = await self._load(user_id)
        user.full_name = data.full_name
        await self.session.flush()
        return self.to_response(user)

    async def change_password(self, user_id: uuid.UUID, data: ChangePasswordRequest) -> tuple[UserResponse, TokenPair]:
        user = await self._load(user_id)
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "WRONG_PASSWORD", "message": "Current password is incorrect"},
            )
        user.password_hash = hash_password(data.new_password)
        # Sign out every other device, then give this one a fresh session
        await self.repo.revoke_all_refresh_tokens(user.id)
        return self.to_response(user), await self._issue_tokens(user)
