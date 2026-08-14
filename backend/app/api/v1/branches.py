"""Branch campuses CRUD + QR."""

from typing import Optional
from uuid import UUID
import base64
import io

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ForbiddenError
from app.core.response import success
from app.models import UserRole
from app.services import branch_service

router = APIRouter(prefix="/branches", tags=["branches"])


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = None
    latitude: float
    longitude: float
    geofence_radius_m: float = Field(default=200, ge=20, le=5000)
    staff_start: str = "09:00"
    staff_end: str = "18:00"
    student_start: str = "09:00"
    student_end: str = "17:00"


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius_m: Optional[float] = Field(default=None, ge=20, le=5000)
    staff_start: Optional[str] = None
    staff_end: Optional[str] = None
    student_start: Optional[str] = None
    student_end: Optional[str] = None


def _qr_image(payload: str) -> str:
    import qrcode

    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


@router.get("")
async def list_branches(user: CurrentUser, db: DbSession):
    await branch_service.ensure_default_branches(db)
    items = await branch_service.list_branches(db)
    # Attach QR images for admins
    if user.role.name in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        for item in items:
            item["qr_image"] = _qr_image(item["punch_payload"])
    else:
        for item in items:
            item.pop("punch_token", None)
            item.pop("punch_payload", None)
    return success({"items": items, "total": len(items)})


@router.post("")
async def create_branch(payload: BranchCreate, user: CurrentUser, db: DbSession):
    created = await branch_service.create_branch(
        db,
        actor=user,
        **payload.model_dump(),
    )
    created["qr_image"] = _qr_image(created["punch_payload"])
    return success(created, message="Branch created", status_code=201)


@router.put("/{branch_id}")
async def update_branch(branch_id: UUID, payload: BranchUpdate, user: CurrentUser, db: DbSession):
    updated = await branch_service.update_branch(
        db, actor=user, branch_id=branch_id, updates=payload.model_dump(exclude_none=True)
    )
    updated["qr_image"] = _qr_image(updated["punch_payload"])
    return success(updated, message="Branch updated")


@router.post("/{branch_id}/qr/rotate")
async def rotate_qr(branch_id: UUID, user: CurrentUser, db: DbSession):
    updated = await branch_service.rotate_branch_qr(db, actor=user, branch_id=branch_id)
    updated["qr_image"] = _qr_image(updated["punch_payload"])
    return success(updated, message="Branch QR rotated")


@router.delete("/{branch_id}")
async def delete_branch(branch_id: UUID, user: CurrentUser, db: DbSession):
    return success(await branch_service.deactivate_branch(db, actor=user, branch_id=branch_id), message="Branch deactivated")
