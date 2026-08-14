from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Request, UploadFile

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ValidationAppError
from app.core.response import success
from app.models import Student
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    UserOut,
)
from app.services import auth_service
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["auth"])

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "uploads" / "avatars"


@router.post("/login")
async def login(payload: LoginRequest, request: Request, db: DbSession):
    user = await auth_service.authenticate_user(db, payload.email, payload.password)
    data = await auth_service.issue_tokens(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return success(data.model_dump(mode="json"), message="Login successful")


@router.post("/google")
async def google_login(payload: GoogleLoginRequest, request: Request, db: DbSession):
    user = await auth_service.authenticate_google(db, payload.id_token)
    data = await auth_service.issue_tokens(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return success(data.model_dump(mode="json"), message="Google sign-in successful")


@router.post("/refresh")
async def refresh(payload: RefreshRequest, request: Request, db: DbSession):
    data = await auth_service.refresh_tokens(
        db,
        payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return success(data.model_dump(mode="json"), message="Token refreshed")


@router.post("/logout")
async def logout(payload: RefreshRequest, db: DbSession):
    await auth_service.logout(db, payload.refresh_token)
    return success(message="Logged out")


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: DbSession):
    from app.core.config import get_settings

    token = await auth_service.request_password_reset(db, payload.email)
    # Never expose reset tokens outside development
    data = {"emailed": bool(token)}
    if get_settings().is_development and token:
        data["reset_token"] = token
    return success(
        data,
        message="If the account exists, reset instructions have been sent",
    )


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: DbSession):
    await auth_service.reset_password(db, payload.token, payload.new_password)
    return success(message="Password reset successful")


@router.get("/me")
async def me(user: CurrentUser):
    return success(UserOut.model_validate(user).model_dump(mode="json"))


@router.post("/me/photo")
async def upload_my_photo(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_PHOTO_TYPES:
        raise ValidationAppError("Only JPEG, PNG, WebP, or GIF images are allowed")
    raw = await file.read()
    if not raw:
        raise ValidationAppError("Empty file")
    if len(raw) > MAX_PHOTO_BYTES:
        raise ValidationAppError("Image must be under 5 MB")

    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }[content_type]
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{user.id}_{uuid4().hex}{ext}"
    path = UPLOAD_ROOT / filename
    path.write_bytes(raw)

    photo_url = f"/uploads/avatars/{filename}"
    user.photo_url = photo_url

    student = await db.scalar(select(Student).where(Student.user_id == user.id))
    if student:
        student.photo_url = photo_url

    await db.flush()
    return success(
        UserOut.model_validate(user).model_dump(mode="json"),
        message="Profile photo updated",
    )


@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, user: CurrentUser, db: DbSession):
    await auth_service.change_password(db, user, payload.current_password, payload.new_password)
    return success(message="Password changed")
