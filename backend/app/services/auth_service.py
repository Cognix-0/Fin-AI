from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password, create_access_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def register(self, data: RegisterRequest) -> UserResponse:
        """
        Register a new user:
        1. Check email is unique
        2. Hash password
        3. Create user record
        4. Assign default EMPLOYEE role
        """
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EMAIL_TAKEN",
                    "message": "An account with this email already exists",
                },
            )

        password_hash = hash_password(data.password)
        user = await self.repo.create(
            email=data.email,
            password_hash=password_hash,
            full_name=data.full_name,
        )

        # All new users get EMPLOYEE role — never ADMIN
        await self.repo.assign_role(user, "EMPLOYEE")

        roles = ["EMPLOYEE"]
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=roles,
            created_at=user.created_at,
        )

    async def login(self, data: LoginRequest) -> tuple[UserResponse, str]:
        """
        Authenticate a user:
        1. Find user by email
        2. Verify password
        3. Return user info + signed JWT
        """
        user = await self.repo.get_by_email(data.email)
        if not user:
            # Use same error message as invalid password — don't leak user existence
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                },
            )

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                },
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ACCOUNT_INACTIVE",
                    "message": "Your account has been deactivated. Contact support.",
                },
            )

        role_names = self.repo.get_role_names(user)
        token = create_access_token(subject=str(user.id), roles=role_names)

        user_response = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=role_names,
            created_at=user.created_at,
        )
        return user_response, token

    async def get_me(self, user_id: str) -> UserResponse:
        """Return the currently authenticated user's profile."""
        import uuid
        user = await self.repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            )
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=self.repo.get_role_names(user),
            created_at=user.created_at,
        )
