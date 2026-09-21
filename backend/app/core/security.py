import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from app.core.config import settings


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT tokens ────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    roles: list[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,         # user id (UUID string)
        "roles": roles,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises jwt.InvalidTokenError on failure.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
    )
    return payload
