"""Academy branches (campuses) with punch GPS + QR."""

from __future__ import annotations

import re
import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models import Branch, User, UserRole


def _require_admin(actor: User) -> None:
    if actor.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError("Only Admin can manage branches")


def _slug_code(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().upper()).strip("-")
    return (slug or "BRANCH")[:40]


async def _unique_code(db: AsyncSession, base: str) -> str:
    code = base[:40]
    n = 2
    while await db.scalar(select(Branch).where(Branch.code == code)):
        suffix = f"-{n}"
        code = f"{base[: 40 - len(suffix)]}{suffix}"
        n += 1
    return code


def _branch_dict(b: Branch) -> dict:
    return {
        "id": str(b.id),
        "code": b.code,
        "name": b.name,
        "address": b.address,
        "latitude": b.latitude,
        "longitude": b.longitude,
        "geofence_radius_m": b.geofence_radius_m,
        "punch_token": b.punch_token,
        "punch_payload": f"caa-punch:{b.punch_token}",
        "staff_start": b.staff_start or "09:00",
        "staff_end": b.staff_end or "18:00",
        "student_start": b.student_start or "09:00",
        "student_end": b.student_end or "17:00",
        "is_active": b.is_active,
    }


async def list_branches(db: AsyncSession, *, active_only: bool = True) -> list[dict]:
    stmt = select(Branch).order_by(Branch.name.asc())
    if active_only:
        stmt = stmt.where(Branch.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    return [_branch_dict(b) for b in rows]


async def create_branch(
    db: AsyncSession,
    *,
    actor: User,
    name: str,
    latitude: float,
    longitude: float,
    code: Optional[str] = None,
    address: Optional[str] = None,
    geofence_radius_m: float = 200,
    staff_start: str = "09:00",
    staff_end: str = "18:00",
    student_start: str = "09:00",
    student_end: str = "17:00",
) -> dict:
    _require_admin(actor)
    name = name.strip()
    if not name:
        raise ValidationAppError("Branch name is required")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValidationAppError("Invalid latitude/longitude")

    raw_code = (code or "").strip().upper() or _slug_code(name)
    unique_code = await _unique_code(db, raw_code)

    branch = Branch(
        code=unique_code,
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        geofence_radius_m=geofence_radius_m,
        punch_token=secrets.token_urlsafe(24),
        staff_start=staff_start,
        staff_end=staff_end,
        student_start=student_start,
        student_end=student_end,
    )
    db.add(branch)
    await db.flush()
    return _branch_dict(branch)


async def update_branch(
    db: AsyncSession,
    *,
    actor: User,
    branch_id: UUID,
    updates: dict,
) -> dict:
    _require_admin(actor)
    branch = await db.scalar(select(Branch).where(Branch.id == branch_id))
    if not branch or not branch.is_active:
        raise NotFoundError("Branch not found")

    for key in (
        "name",
        "address",
        "latitude",
        "longitude",
        "geofence_radius_m",
        "staff_start",
        "staff_end",
        "student_start",
        "student_end",
    ):
        if key in updates and updates[key] is not None:
            setattr(branch, key, updates[key])
    await db.flush()
    return _branch_dict(branch)


async def rotate_branch_qr(db: AsyncSession, *, actor: User, branch_id: UUID) -> dict:
    _require_admin(actor)
    branch = await db.scalar(select(Branch).where(Branch.id == branch_id, Branch.is_active.is_(True)))
    if not branch:
        raise NotFoundError("Branch not found")
    branch.punch_token = secrets.token_urlsafe(24)
    await db.flush()
    return _branch_dict(branch)


async def deactivate_branch(db: AsyncSession, *, actor: User, branch_id: UUID) -> dict:
    _require_admin(actor)
    branch = await db.scalar(select(Branch).where(Branch.id == branch_id))
    if not branch:
        raise NotFoundError("Branch not found")
    branch.is_active = False
    await db.flush()
    return {"id": str(branch.id), "is_active": False}


async def ensure_default_branches(db: AsyncSession) -> None:
    """Seed Headquarters only if no branches exist; deactivate sample East/North/Hall branches."""
    existing = await db.scalar(select(Branch.id).limit(1))
    if not existing:
        db.add(
            Branch(
                code="BR-HQ",
                name="Headquarters",
                address="Main Campus",
                latitude=28.6139,
                longitude=77.2090,
                geofence_radius_m=200,
                punch_token=secrets.token_urlsafe(24),
            )
        )
        await db.flush()

    # Remove demo campuses the academy doesn't use
    sample_codes = {"BR-NORTH", "BR-EAST"}
    rows = (await db.execute(select(Branch).where(Branch.is_active.is_(True)))).scalars().all()
    for branch in rows:
        name_l = (branch.name or "").lower().strip()
        addr_l = (branch.address or "").lower()
        if branch.code in sample_codes:
            branch.is_active = False
            continue
        if name_l in {"hall", "exam hall", "exam hall 1"} or name_l.endswith(" hall"):
            branch.is_active = False
            continue
        if "east campus" in addr_l or "north campus" in addr_l:
            if branch.code != "BR-HQ":
                branch.is_active = False
    await db.flush()
