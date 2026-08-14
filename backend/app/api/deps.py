from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import role_has_permission
from app.core.security import try_decode_token
from app.db.session import get_db
from app.models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication required")

    payload = try_decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")
    try:
        uid = UUID(user_id)
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid token subject")

    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == uid, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found or inactive")

    request.state.user = user
    return user


def require_permissions(*permissions: str):
    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        role = user.role.name if user.role else None
        if role is None:
            raise ForbiddenError("Role not assigned")
        for perm in permissions:
            if not role_has_permission(role, perm, user.extra_permissions or {}):
                raise ForbiddenError(f"Missing permission: {perm}")
        return user

    return dependency


def require_roles(*roles: UserRole):
    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not user.role or user.role.name not in roles:
            raise ForbiddenError("Insufficient role")
        return user

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
