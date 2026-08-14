from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.core.response import success
from app.models import Course, LeadSource, LeadStatus, LeadTemperature, Staff, User, UserRole
from app.schemas.leads import (
    CallActivityCreate,
    LeadAssign,
    LeadCreate,
    LeadDetailOut,
    LeadOut,
    LeadUpdate,
    WebsiteEnquiry,
)
from app.services import import_service, lead_service
from app.services.notification_service import notify_users
from app.services.scoring_service import calculate_lead_score

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadImportCommit(BaseModel):
    rows: list[dict] = Field(default_factory=list)
    auto_assign: bool = True
    skip_invalid: bool = True
    skip_duplicates: bool = False


async def _staff_for_user(db: DbSession, user: User) -> Optional[Staff]:
    return await db.scalar(select(Staff).where(Staff.user_id == user.id))


def _lead_to_detail(lead, duplicates=None) -> dict:
    assigned_name = None
    if lead.assigned_staff and lead.assigned_staff.user:
        assigned_name = lead.assigned_staff.user.full_name
    course_name = lead.course.name if lead.course else None
    data = LeadDetailOut(
        **LeadOut.model_validate(lead).model_dump(),
        activities=lead.activities or [],
        followups=lead.followups or [],
        assigned_staff_name=assigned_name,
        course_name=course_name,
        duplicates=[LeadOut.model_validate(d) for d in (duplicates or [])],
    )
    return data.model_dump(mode="json")


@router.get("")
async def list_leads(
    user: CurrentUser,
    db: DbSession,
    status: Optional[LeadStatus] = None,
    temperature: Optional[LeadTemperature] = None,
    source: Optional[LeadSource] = None,
    course_id: Optional[UUID] = None,
    staff_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    # Permission soft-check
    if user.role.name not in {
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.RM,
        UserRole.TELECALLER,
    }:
        raise ForbiddenError("CRM access denied")

    leads, total = await lead_service.list_leads(
        db,
        user=user,
        status=status,
        temperature=temperature,
        source=source,
        course_id=course_id,
        staff_id=staff_id,
        search=search,
        skip=skip,
        limit=limit,
    )
    return success(
        {
            "items": [LeadOut.model_validate(l).model_dump(mode="json") for l in leads],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    )


@router.post("")
async def create_lead(
    payload: LeadCreate,
    user: CurrentUser,
    db: DbSession,
):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM, UserRole.TELECALLER}:
        raise ForbiddenError("Cannot create leads")

    lead, duplicates = await lead_service.create_lead(
        db,
        name=payload.name,
        phone=payload.phone,
        source=payload.source,
        email=payload.email,
        location=payload.location,
        age=payload.age,
        course_id=payload.course_id,
        notes=payload.notes,
        message=payload.message,
        created_by=user,
        auto_assign=payload.auto_assign,
    )
    lead = await lead_service.get_lead(db, lead.id)
    msg = "Lead created successfully"
    if duplicates:
        msg = "Lead created. Possible duplicate lead found."
    return JSONResponse(
        status_code=201,
        content=success(_lead_to_detail(lead, duplicates), message=msg, status_code=201),
    )


@router.get("/import/template")
async def download_import_template(user: CurrentUser):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    content = import_service.build_template_bytes()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="calibre_leads_import_template.xlsx"'},
    )


@router.post("/import/preview")
async def preview_lead_import(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    raw = await file.read()
    if not raw:
        raise ValidationAppError("Empty file")
    try:
        preview = await import_service.preview_import(db, raw, file.filename or "upload.xlsx")
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc
    return success(preview, message="Import preview ready")


@router.post("/import/commit")
async def commit_lead_import(payload: LeadImportCommit, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    if not payload.rows:
        raise ValidationAppError("No rows to import")
    result = await import_service.commit_import(
        db,
        rows=payload.rows,
        created_by=user,
        auto_assign=payload.auto_assign,
        skip_invalid=payload.skip_invalid,
        skip_duplicates=payload.skip_duplicates,
    )
    return JSONResponse(
        status_code=201,
        content=success(
            result,
            message=f"Imported {result['created']} lead(s)",
            status_code=201,
        ),
    )


@router.post("/website-enquiry", include_in_schema=True)
async def website_enquiry(payload: WebsiteEnquiry, db: DbSession):
    """Public website integration endpoint — creates CRM lead and notifies RMs."""
    course_id = None
    if payload.course:
        course = await db.scalar(
            select(Course).where(
                (Course.code.ilike(payload.course)) | (Course.name.ilike(f"%{payload.course}%"))
            )
        )
        if course:
            course_id = course.id

    lead, duplicates = await lead_service.create_lead(
        db,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        source=LeadSource.WEBSITE,
        course_id=course_id,
        message=payload.message,
        auto_assign=True,
    )

    # Notify RMs
    from app.models import Role

    rms = (
        await db.execute(
            select(User)
            .join(Role)
            .where(Role.name.in_([UserRole.RM, UserRole.ADMIN, UserRole.SUPER_ADMIN]), User.is_active.is_(True))
        )
    ).scalars().all()
    await notify_users(
        db,
        user_ids=[u.id for u in rms],
        title="New website lead",
        body=f"{payload.name} enquired via website.",
        category="website_lead",
        link=f"/leads/{lead.id}",
    )

    lead = await lead_service.get_lead(db, lead.id)
    return JSONResponse(
        status_code=201,
        content=success(
            {"lead_id": str(lead.id), "lead_code": lead.lead_code, "duplicate_warning": bool(duplicates)},
            message="Enquiry received",
            status_code=201,
        ),
    )


@router.get("/{lead_id}")
async def get_lead(lead_id: UUID, user: CurrentUser, db: DbSession):
    lead = await lead_service.get_lead(db, lead_id)
    staff = await _staff_for_user(db, user)
    await lead_service.ensure_lead_access(user, lead, staff)
    duplicates = await lead_service.find_duplicate_leads(db, lead.phone, lead.email, exclude_id=lead.id)
    return success(_lead_to_detail(lead, duplicates))


@router.patch("/{lead_id}")
async def update_lead(lead_id: UUID, payload: LeadUpdate, user: CurrentUser, db: DbSession):
    lead = await lead_service.get_lead(db, lead_id)
    staff = await _staff_for_user(db, user)
    await lead_service.ensure_lead_access(user, lead, staff)

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(lead, k, v)
    lead.updated_by_id = user.id
    lead.score = await calculate_lead_score(db, lead)
    await db.flush()
    lead = await lead_service.get_lead(db, lead.id)
    return success(_lead_to_detail(lead), message="Lead updated successfully")


@router.post("/{lead_id}/assign")
async def assign_lead(
    lead_id: UUID,
    payload: LeadAssign,
    user: CurrentUser,
    db: DbSession,
):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError("Only RM/Admin can assign leads")
    lead = await lead_service.get_lead(db, lead_id)
    await lead_service.assign_lead_manual(db, lead, payload.staff_id, assigned_by=user, notes=payload.notes)
    lead = await lead_service.get_lead(db, lead_id)
    return success(_lead_to_detail(lead), message="Lead assigned")


@router.post("/{lead_id}/auto-assign")
async def auto_assign_lead(lead_id: UUID, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError("Only RM/Admin can auto-assign leads")
    lead = await lead_service.get_lead(db, lead_id)
    await lead_service.assign_lead_round_robin(db, lead, assigned_by=user)
    lead = await lead_service.get_lead(db, lead_id)
    return success(_lead_to_detail(lead), message="Lead auto-assigned")


@router.post("/{lead_id}/activities")
async def add_call_activity(
    lead_id: UUID,
    payload: CallActivityCreate,
    user: CurrentUser,
    db: DbSession,
):
    lead = await lead_service.get_lead(db, lead_id)
    staff = await _staff_for_user(db, user)
    await lead_service.ensure_lead_access(user, lead, staff)
    if not staff:
        raise ForbiddenError("Staff profile required")

    await lead_service.record_call_activity(
        db,
        lead=lead,
        staff=staff,
        call_outcome=payload.call_outcome,
        temperature=payload.temperature,
        feedback=payload.feedback,
        duration_seconds=payload.duration_seconds,
        next_follow_up_at=payload.next_follow_up_at,
        interest_not_interested=payload.not_interested,
    )
    lead = await lead_service.get_lead(db, lead_id)
    return success(_lead_to_detail(lead), message="Call activity recorded")
