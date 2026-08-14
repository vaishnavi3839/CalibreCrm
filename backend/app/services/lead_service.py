from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models import (
    AssignmentCursor,
    Lead,
    LeadActivity,
    LeadAssignment,
    LeadFollowUp,
    LeadScoreRule,
    LeadSource,
    LeadStatus,
    LeadTemperature,
    CallOutcome,
    FollowUpStatus,
    Notification,
    NotificationChannel,
    Staff,
    User,
    UserRole,
)
from app.services.notification_service import notify_user
from app.services.scoring_service import calculate_lead_score

settings = get_settings()


async def generate_lead_code(db: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    count = await db.scalar(select(func.count()).select_from(Lead)) or 0
    return f"CAA-L-{year}-{count + 1:05d}"


async def find_duplicate_leads(
    db: AsyncSession, phone: str, email: Optional[str] = None, exclude_id: Optional[UUID] = None
) -> list[Lead]:
    conditions = [Lead.phone == phone, Lead.is_active.is_(True)]
    if email:
        conditions = [or_(Lead.phone == phone, Lead.email == email), Lead.is_active.is_(True)]
    stmt = select(Lead).where(and_(*conditions) if email else and_(Lead.phone == phone, Lead.is_active.is_(True)))
    if exclude_id:
        stmt = stmt.where(Lead.id != exclude_id)
    result = await db.execute(stmt.limit(5))
    return list(result.scalars().all())


async def create_lead(
    db: AsyncSession,
    *,
    name: str,
    phone: str,
    source: LeadSource,
    email: Optional[str] = None,
    location: Optional[str] = None,
    age: Optional[int] = None,
    course_id: Optional[UUID] = None,
    notes: Optional[str] = None,
    message: Optional[str] = None,
    created_by: Optional[User] = None,
    auto_assign: bool = False,
) -> tuple[Lead, list[Lead]]:
    duplicates = await find_duplicate_leads(db, phone, email)
    lead = Lead(
        lead_code=await generate_lead_code(db),
        name=name,
        phone=phone,
        email=email,
        location=location,
        age=age,
        course_id=course_id,
        source=source,
        status=LeadStatus.NEW,
        notes=notes,
        message=message,
        created_by_id=created_by.id if created_by else None,
        score=0,
    )
    db.add(lead)
    await db.flush()

    db.add(
        LeadActivity(
            lead_id=lead.id,
            activity_type="created",
            feedback=f"Lead created from {source.value}",
            metadata_json={"source": source.value},
        )
    )

    if auto_assign:
        await assign_lead_round_robin(db, lead, assigned_by=created_by)

    await db.flush()
    await db.refresh(lead)
    return lead, duplicates


async def get_lead(db: AsyncSession, lead_id: UUID) -> Lead:
    result = await db.execute(
        select(Lead)
        .options(
            selectinload(Lead.assigned_staff).selectinload(Staff.user),
            selectinload(Lead.course),
            selectinload(Lead.activities),
            selectinload(Lead.followups),
        )
        .where(Lead.id == lead_id, Lead.is_active.is_(True))
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise NotFoundError("Lead not found")
    return lead


async def list_leads(
    db: AsyncSession,
    *,
    user: User,
    status: Optional[LeadStatus] = None,
    temperature: Optional[LeadTemperature] = None,
    source: Optional[LeadSource] = None,
    course_id: Optional[UUID] = None,
    staff_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Lead], int]:
    filters = [Lead.is_active.is_(True)]

    # Telecallers only see assigned leads
    if user.role.name == UserRole.TELECALLER:
        staff = await db.scalar(select(Staff).where(Staff.user_id == user.id))
        if not staff:
            return [], 0
        filters.append(Lead.assigned_staff_id == staff.id)
    elif staff_id:
        filters.append(Lead.assigned_staff_id == staff_id)

    if status:
        filters.append(Lead.status == status)
    if temperature:
        filters.append(Lead.temperature == temperature)
    if source:
        filters.append(Lead.source == source)
    if course_id:
        filters.append(Lead.course_id == course_id)
    if search:
        q = f"%{search.strip()}%"
        filters.append(
            or_(
                Lead.name.ilike(q),
                Lead.phone.ilike(q),
                Lead.email.ilike(q),
                Lead.lead_code.ilike(q),
            )
        )

    total = await db.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0
    result = await db.execute(
        select(Lead)
        .options(selectinload(Lead.assigned_staff).selectinload(Staff.user), selectinload(Lead.course))
        .where(*filters)
        .order_by(Lead.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
    )
    return list(result.scalars().all()), total


async def assign_lead_manual(
    db: AsyncSession, lead: Lead, staff_id: UUID, assigned_by: Optional[User] = None, notes: Optional[str] = None
) -> Lead:
    staff = await db.get(Staff, staff_id)
    if not staff or not staff.is_active:
        raise NotFoundError("Staff not found")

    # Mark previous assignments inactive
    result = await db.execute(
        select(LeadAssignment).where(LeadAssignment.lead_id == lead.id, LeadAssignment.is_current.is_(True))
    )
    for prev in result.scalars().all():
        prev.is_current = False

    db.add(
        LeadAssignment(
            lead_id=lead.id,
            staff_id=staff_id,
            assigned_by_id=assigned_by.id if assigned_by else None,
            method="manual",
            notes=notes,
            is_current=True,
        )
    )
    lead.assigned_staff_id = staff_id
    if lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.ASSIGNED

    db.add(
        LeadActivity(
            lead_id=lead.id,
            staff_id=staff_id,
            activity_type="assigned",
            feedback=f"Manually assigned to {staff.employee_code}",
            metadata_json={"method": "manual"},
        )
    )

    if staff.user_id:
        await notify_user(
            db,
            user_id=staff.user_id,
            title="New lead assigned",
            body=f"{lead.name} ({lead.lead_code}) has been assigned to you.",
            category="lead_assigned",
            link=f"/leads/{lead.id}",
        )

    await db.flush()
    return lead


async def assign_lead_round_robin(
    db: AsyncSession, lead: Lead, assigned_by: Optional[User] = None
) -> Optional[Lead]:
    result = await db.execute(
        select(Staff)
        .options(selectinload(Staff.user).selectinload(User.role))
        .where(
            Staff.is_active.is_(True),
            Staff.is_available_for_leads.is_(True),
        )
        .order_by(Staff.employee_code.asc())
    )
    staff_list = list(result.scalars().all())
    telecallers = [
        s for s in staff_list if s.user and s.user.role and s.user.role.name == UserRole.TELECALLER
    ]

    if not telecallers:
        # Fallback: any available staff
        telecallers = staff_list
    if not telecallers:
        return None

    cursor = await db.scalar(select(AssignmentCursor).where(AssignmentCursor.strategy == "round_robin"))
    if not cursor:
        cursor = AssignmentCursor(strategy="round_robin")
        db.add(cursor)
        await db.flush()

    next_index = 0
    if cursor.last_staff_id:
        for i, s in enumerate(telecallers):
            if s.id == cursor.last_staff_id:
                next_index = (i + 1) % len(telecallers)
                break

    chosen = telecallers[next_index]
    cursor.last_staff_id = chosen.id

    # Mark previous current assignments
    prev = await db.execute(
        select(LeadAssignment).where(LeadAssignment.lead_id == lead.id, LeadAssignment.is_current.is_(True))
    )
    for p in prev.scalars().all():
        p.is_current = False

    db.add(
        LeadAssignment(
            lead_id=lead.id,
            staff_id=chosen.id,
            assigned_by_id=assigned_by.id if assigned_by else None,
            method="round_robin",
            is_current=True,
        )
    )
    lead.assigned_staff_id = chosen.id
    if lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.ASSIGNED

    db.add(
        LeadActivity(
            lead_id=lead.id,
            staff_id=chosen.id,
            activity_type="assigned",
            feedback=f"Round-robin assigned to {chosen.employee_code}",
            metadata_json={"method": "round_robin"},
        )
    )

    if chosen.user_id:
        await notify_user(
            db,
            user_id=chosen.user_id,
            title="New lead assigned",
            body=f"{lead.name} ({lead.lead_code}) has been assigned to you.",
            category="lead_assigned",
            link=f"/leads/{lead.id}",
        )

    await db.flush()
    return lead


async def record_call_activity(
    db: AsyncSession,
    *,
    lead: Lead,
    staff: Staff,
    call_outcome: CallOutcome,
    temperature: Optional[LeadTemperature] = None,
    feedback: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    next_follow_up_at: Optional[datetime] = None,
    interest_not_interested: bool = False,
) -> Lead:
    # Ensure telecaller owns the lead
    if lead.assigned_staff_id and lead.assigned_staff_id != staff.id:
        # Admins/RM can still act — caller of this function should check
        pass

    lead.last_contacted_at = datetime.now(timezone.utc)

    if call_outcome == CallOutcome.CONNECTED:
        if lead.status in {LeadStatus.NEW, LeadStatus.ASSIGNED}:
            lead.status = LeadStatus.CONTACTED
        if temperature:
            lead.temperature = temperature
            if temperature == LeadTemperature.HOT and lead.status == LeadStatus.CONTACTED:
                lead.status = LeadStatus.INTERESTED
        if interest_not_interested:
            lead.status = LeadStatus.NOT_INTERESTED
            lead.temperature = LeadTemperature.COLD
    elif call_outcome == CallOutcome.WRONG_NUMBER:
        lead.status = LeadStatus.INVALID_NUMBER

    db.add(
        LeadActivity(
            lead_id=lead.id,
            staff_id=staff.id,
            activity_type="call",
            call_outcome=call_outcome,
            duration_seconds=duration_seconds,
            temperature=temperature,
            feedback=feedback,
        )
    )

    if next_follow_up_at:
        db.add(
            LeadFollowUp(
                lead_id=lead.id,
                staff_id=staff.id,
                scheduled_at=next_follow_up_at,
                status=FollowUpStatus.PENDING,
                notes=feedback,
            )
        )
        lead.next_follow_up_at = next_follow_up_at
        if lead.status not in {LeadStatus.NOT_INTERESTED, LeadStatus.LOST, LeadStatus.CONVERTED}:
            lead.status = LeadStatus.FOLLOW_UP

    lead.score = await calculate_lead_score(db, lead)
    await db.flush()
    return lead


async def ensure_lead_access(user: User, lead: Lead, staff: Optional[Staff]) -> None:
    role = user.role.name
    if role in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        return
    if role == UserRole.TELECALLER:
        if not staff or lead.assigned_staff_id != staff.id:
            raise ForbiddenError("You can only access leads assigned to you")
        return
    raise ForbiddenError("CRM access denied")
