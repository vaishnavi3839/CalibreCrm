from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    hash_token,
    password_reset_expiry,
    refresh_token_expiry,
    verify_password,
)
from app.models import PasswordResetToken, RefreshToken, User
from app.schemas.auth import AuthResponse, TokenPair, UserOut


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    return user


async def authenticate_google(db: AsyncSession, id_token: str) -> User:
    """Verify Google ID token and match an already-provisioned academy user by email."""
    import httpx

    settings = get_settings()
    if not settings.google_client_id:
        raise ValidationAppError("Google Sign-In is not configured. Set GOOGLE_CLIENT_ID.")

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )
    if res.status_code != 200:
        raise UnauthorizedError("Invalid Google token")

    payload = res.json()
    aud = payload.get("aud")
    email = (payload.get("email") or "").lower().strip()
    email_verified = str(payload.get("email_verified", "")).lower() in {"true", "1"}

    if aud != settings.google_client_id:
        raise UnauthorizedError("Google token audience mismatch")
    if not email or not email_verified:
        raise UnauthorizedError("Google account email is not verified")

    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError(
            "No academy account found for this Google email. Ask Admin to add you first."
        )

    # Prefer Google profile photo when user has none
    picture = payload.get("picture")
    if picture and not user.photo_url:
        user.photo_url = picture
    return user


async def issue_tokens(
    db: AsyncSession,
    user: User,
    *,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuthResponse:
    settings = get_settings()
    access = create_access_token(str(user.id), user.role.name.value)
    refresh = create_refresh_token_value()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=refresh_token_expiry(),
            user_agent=user_agent,
            ip_address=ip_address,
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    return AuthResponse(
        user=UserOut.model_validate(user),
        tokens=TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
    )


async def refresh_tokens(
    db: AsyncSession,
    refresh_token: str,
    *,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuthResponse:
    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Invalid or expired refresh token")

    user_result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == stored.user_id, User.is_active.is_(True))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")

    stored.revoked_at = datetime.now(timezone.utc)
    return await issue_tokens(db, user, user_agent=user_agent, ip_address=ip_address)


async def logout(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        await db.flush()


async def request_password_reset(db: AsyncSession, email: str) -> str:
    result = await db.execute(select(User).where(User.email == email.lower(), User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    # Always return a token-like message in prod; in dev return token for testing.
    if not user:
        return ""

    raw = create_refresh_token_value()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=password_reset_expiry(),
        )
    )
    await db.flush()
    return raw


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    if len(new_password) < 8:
        raise ValidationAppError("Password must be at least 8 characters")
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(token),
            PasswordResetToken.used_at.is_(None),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise ValidationAppError("Invalid or expired reset token")

    user = await db.get(User, stored.user_id)
    if not user:
        raise NotFoundError("User not found")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    stored.used_at = datetime.now(timezone.utc)
    await db.flush()


async def change_password(db: AsyncSession, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")
    if len(new_password) < 8:
        raise ValidationAppError("Password must be at least 8 characters")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await db.flush()
