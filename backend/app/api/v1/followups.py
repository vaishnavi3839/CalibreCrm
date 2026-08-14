from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.response import success
from app.models import FollowUpStatus, Lead, LeadFollowUp, LeadTemperature, Staff, User, UserRole
from app.services.notification_service import notify_users

router = APIRouter(prefix="/followups", tags=["followups"])


@router.get("")
async def list_followups(
    user: CurrentUser,
    db: DbSession,
    status: Optional[FollowUpStatus] = None,
    today_only: bool = False,
    skip: int = 0,
    limit: int = 50,
):
    filters = []
    if user.role.name == UserRole.TELECALLER:
        staff = await db.scalar(select(Staff).where(Staff.user_id == user.id))
        if not staff:
            return success({"items": [], "total": 0})
        filters.append(LeadFollowUp.staff_id == staff.id)
    elif user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()

    if status:
        filters.append(LeadFollowUp.status == status)
    if today_only:
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)
        filters.append(LeadFollowUp.scheduled_at >= start)
        filters.append(LeadFollowUp.scheduled_at <= end)

    stmt = (
        select(LeadFollowUp)
        .options(selectinload(LeadFollowUp.lead), selectinload(LeadFollowUp.staff).selectinload(Staff.user))
        .where(*filters)
        .order_by(LeadFollowUp.scheduled_at.asc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    items = []
    for f in rows:
        items.append(
            {
                "id": str(f.id),
                "lead_id": str(f.lead_id),
                "lead_name": f.lead.name if f.lead else None,
                "lead_temperature": f.lead.temperature.value if f.lead and f.lead.temperature else None,
                "staff_id": str(f.staff_id),
                "staff_name": f.staff.user.full_name if f.staff and f.staff.user else None,
                "scheduled_at": f.scheduled_at.isoformat(),
                "status": f.status.value,
                "notes": f.notes,
            }
        )
    return success({"items": items, "total": len(items)})


@router.post("/{followup_id}/complete")
async def complete_followup(followup_id: UUID, user: CurrentUser, db: DbSession):
    fu = await db.get(LeadFollowUp, followup_id)
    if not fu:
        raise NotFoundError("Follow-up not found")
    fu.status = FollowUpStatus.COMPLETED
    fu.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return success(message="Follow-up completed")


@router.post("/mark-overdue")
async def mark_overdue(user: CurrentUser, db: DbSession):
    """Mark missed follow-ups and escalate HOT lead misses to RM."""
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()

    now = datetime.now(timezone.utc)
    pending = (
        await db.execute(
            select(LeadFollowUp)
            .options(selectinload(LeadFollowUp.lead))
            .where(LeadFollowUp.status == FollowUpStatus.PENDING, LeadFollowUp.scheduled_at < now)
        )
    ).scalars().all()

    hot_misses = []
    for fu in pending:
        fu.status = FollowUpStatus.MISSED
        if fu.lead and fu.lead.temperature == LeadTemperature.HOT:
            hot_misses.append(fu)

    if hot_misses:
        from app.models import Role

        rms = (
            await db.execute(
                select(User).join(Role).where(Role.name.in_([UserRole.RM, UserRole.ADMIN]), User.is_active.is_(True))
            )
        ).scalars().all()
        for fu in hot_misses:
            await notify_users(
                db,
                user_ids=[u.id for u in rms],
                title="IMPORTANT — HOT LEAD FOLLOW-UP MISSED",
                body=f"Hot lead {fu.lead.name} ({fu.lead.lead_code}) follow-up was missed.",
                category="hot_lead_missed",
                link=f"/leads/{fu.lead_id}",
            )

    await db.flush()
    return success({"marked_missed": len(pending), "hot_escalations": len(hot_misses)})
