from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.core.response import success
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    Batch,
    NotificationChannel,
    Parent,
    ParentStudent,
    Staff,
    Student,
    User,
    UserRole,
)
from app.services import user_admin_service
from app.services.notification_service import notify_user

router = APIRouter(tags=["students-attendance"])
settings = get_settings()


class StudentCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: Optional[str] = None
    student_code: Optional[str] = None
    course_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    password: Optional[str] = Field(default=None, min_length=8)


class ParentCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: Optional[str] = None
    relationship_type: str = "parent"
    student_id: Optional[UUID] = None
    password: Optional[str] = Field(default=None, min_length=8)


@router.get("/batches")
async def list_batches(user: CurrentUser, db: DbSession):
    if user.role.name in {UserRole.STUDENT, UserRole.PARENT, UserRole.TELECALLER}:
        raise ForbiddenError()
    rows = (
        await db.execute(
            select(Batch).where(Batch.is_active.is_(True), Batch.status == "active").order_by(Batch.name)
        )
    ).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(b.id),
                    "code": b.code,
                    "name": b.name,
                    "course_id": str(b.course_id) if b.course_id else None,
                }
                for b in rows
            ]
        }
    )


@router.get("/students")
async def list_students(
    user: CurrentUser,
    db: DbSession,
    search: Optional[str] = None,
    batch_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
):
    if user.role.name in {UserRole.STUDENT, UserRole.PARENT, UserRole.TELECALLER}:
        raise ForbiddenError()

    filters = [Student.is_active.is_(True)]
    if user.role.name == UserRole.INSTRUCTOR:
        staff = await db.scalar(select(Staff).where(Staff.user_id == user.id))
        if staff:
            filters.append(Student.instructor_id == staff.id)
    if batch_id:
        filters.append(Student.batch_id == batch_id)
    if search:
        q = f"%{search}%"
        filters.append(Student.student_code.ilike(q))

    rows = (
        await db.execute(
            select(Student)
            .options(
                selectinload(Student.user),
                selectinload(Student.course),
                selectinload(Student.batch),
                selectinload(Student.branch),
            )
            .where(*filters)
            .offset(skip)
            .limit(limit)
        )
    ).scalars().all()

    return success(
        {
            "items": [
                {
                    "id": str(s.id),
                    "student_code": s.student_code,
                    "name": s.user.full_name if s.user else None,
                    "email": s.user.email if s.user else None,
                    "phone": s.user.phone if s.user else None,
                    "course": s.course.name if s.course else None,
                    "batch": s.batch.name if s.batch else None,
                    "batch_id": str(s.batch_id) if s.batch_id else None,
                    "course_id": str(s.course_id) if s.course_id else None,
                    "branch_id": str(s.branch_id) if s.branch_id else None,
                    "branch_name": s.branch.name if s.branch else None,
                    "attendance_pct": s.attendance_pct,
                    "course_progress_pct": s.course_progress_pct,
                    "academic_status": s.academic_status,
                }
                for s in rows
            ]
        }
    )


@router.post("/students")
async def create_student(payload: StudentCreateRequest, user: CurrentUser, db: DbSession):
    created = await user_admin_service.create_student(
        db,
        created_by=user,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        student_code=payload.student_code,
        course_id=payload.course_id,
        batch_id=payload.batch_id,
        branch_id=payload.branch_id,
        password=payload.password,
    )
    return JSONResponse(
        status_code=201,
        content=success(created, message="Student created with login access", status_code=201),
    )


class StudentUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    student_code: Optional[str] = None
    course_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    password: Optional[str] = Field(default=None, min_length=8)
    clear_course: bool = False
    clear_batch: bool = False


@router.put("/students/{student_id}")
async def update_student(student_id: UUID, payload: StudentUpdateRequest, user: CurrentUser, db: DbSession):
    updated = await user_admin_service.update_student(
        db,
        student_id=student_id,
        updated_by=user,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        student_code=payload.student_code,
        course_id=payload.course_id,
        batch_id=payload.batch_id,
        branch_id=payload.branch_id,
        password=payload.password,
        clear_course=payload.clear_course,
        clear_batch=payload.clear_batch,
        clear_branch=False,
    )
    return success(updated, message="Student updated")


@router.put("/students/{student_id}/branch")
async def assign_student_branch(
    student_id: UUID,
    payload: dict,
    user: CurrentUser,
    db: DbSession,
):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError()
    from app.models import Branch

    branch_id = payload.get("branch_id")
    if not branch_id:
        raise ValidationAppError("branch_id is required")
    student = await db.scalar(select(Student).where(Student.id == student_id, Student.is_active.is_(True)))
    if not student:
        raise NotFoundError("Student not found")
    branch = await db.scalar(select(Branch).where(Branch.id == UUID(str(branch_id)), Branch.is_active.is_(True)))
    if not branch:
        raise ValidationAppError("Branch not found")
    student.branch_id = branch.id
    await db.flush()
    return success(
        {"student_id": str(student.id), "branch_id": str(branch.id), "branch_name": branch.name},
        message="Student punch branch updated",
    )


@router.delete("/students/{student_id}")
async def delete_student(student_id: UUID, user: CurrentUser, db: DbSession):
    result = await user_admin_service.deactivate_student(db, student_id=student_id, deleted_by=user)
    return success(result, message="Student deleted")


@router.get("/parents")
async def list_parents(user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    items = await user_admin_service.list_parents(db)
    return success({"items": items, "total": len(items)})


@router.post("/parents")
async def create_parent(payload: ParentCreateRequest, user: CurrentUser, db: DbSession):
    created = await user_admin_service.create_parent(
        db,
        created_by=user,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        relationship_type=payload.relationship_type,
        student_id=payload.student_id,
        password=payload.password,
    )
    return JSONResponse(
        status_code=201,
        content=success(created, message="Parent created with login access", status_code=201),
    )


@router.delete("/parents/{parent_id}")
async def delete_parent(parent_id: UUID, user: CurrentUser, db: DbSession):
    result = await user_admin_service.deactivate_parent(db, parent_id=parent_id, deleted_by=user)
    return success(result, message="Parent deleted")


@router.get("/students/me/profile")
async def my_student_profile(user: CurrentUser, db: DbSession):
    if user.role.name != UserRole.STUDENT:
        raise ForbiddenError()
    student = await db.scalar(select(Student).where(Student.user_id == user.id))
    if not student:
        raise NotFoundError("Student profile not found")
    return await get_student(student.id, user, db)


@router.get("/students/{student_id}")
async def get_student(student_id: UUID, user: CurrentUser, db: DbSession):
    student = await db.scalar(
        select(Student)
        .options(
            selectinload(Student.user),
            selectinload(Student.course),
            selectinload(Student.batch),
        )
        .where(Student.id == student_id)
    )
    if not student:
        raise NotFoundError("Student not found")

    await _ensure_student_access(db, user, student)
    summary = await _attendance_summary(db, student.id)

    return success(
        {
            "id": str(student.id),
            "student_code": student.student_code,
            "name": student.user.full_name if student.user else None,
            "email": student.user.email if student.user else None,
            "phone": student.user.phone if student.user else None,
            "photo_url": student.photo_url or (student.user.photo_url if student.user else None),
            "course": student.course.name if student.course else None,
            "batch": student.batch.name if student.batch else None,
            "enrollment_date": student.enrollment_date.isoformat() if student.enrollment_date else None,
            "attendance_pct": student.attendance_pct,
            "days_present": summary["days_present"],
            "days_absent": summary["days_absent"],
            "days_total": summary["days_total"],
            "course_progress_pct": student.course_progress_pct,
            "training_hours_completed": student.training_hours_completed,
            "academic_status": student.academic_status,
            # no payment fields
        }
    )


@router.post("/attendance")
async def mark_attendance(payload: dict, user: CurrentUser, db: DbSession):
    """Mark attendance for a batch session.

    payload: {
      batch_id, subject_id?, session_date, records: [{student_id, status, remarks?}]
    }
    """
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INSTRUCTOR}:
        raise ForbiddenError()

    batch_id = UUID(payload["batch_id"])
    session_date = date.fromisoformat(payload["session_date"])
    subject_id = UUID(payload["subject_id"]) if payload.get("subject_id") else None
    staff = await db.scalar(select(Staff).where(Staff.user_id == user.id))

    session = AttendanceSession(
        batch_id=batch_id,
        subject_id=subject_id,
        session_date=session_date,
        marked_by_id=staff.id if staff else None,
        notes=payload.get("notes"),
    )
    db.add(session)
    await db.flush()

    absent_students = []
    for rec in payload.get("records", []):
        status = AttendanceStatus(rec["status"])
        record = AttendanceRecord(
            session_id=session.id,
            student_id=UUID(rec["student_id"]),
            status=status,
            remarks=rec.get("remarks"),
        )
        db.add(record)
        if status == AttendanceStatus.ABSENT:
            absent_students.append(UUID(rec["student_id"]))

    await db.flush()

    # Recalc attendance % and notify parents on absence
    for sid in {UUID(r["student_id"]) for r in payload.get("records", [])}:
        await _recalc_attendance(db, sid)

    for sid in absent_students:
        await _notify_absence(db, sid, session_date)

    return success({"session_id": str(session.id)}, message="Attendance marked", status_code=201)


@router.get("/students/{student_id}/attendance")
async def student_attendance(student_id: UUID, user: CurrentUser, db: DbSession):
    student = await db.get(Student, student_id)
    if not student:
        raise NotFoundError("Student not found")
    await _ensure_student_access(db, user, student)

    rows = (
        await db.execute(
            select(AttendanceRecord)
            .options(selectinload(AttendanceRecord.session))
            .where(AttendanceRecord.student_id == student_id)
            .order_by(AttendanceRecord.created_at.desc())
            .limit(100)
        )
    ).scalars().all()

    summary = await _attendance_summary(db, student_id)

    return success(
        {
            "attendance_pct": student.attendance_pct,
            "days_present": summary["days_present"],
            "days_absent": summary["days_absent"],
            "days_total": summary["days_total"],
            "records": [
                {
                    "id": str(r.id),
                    "status": r.status.value,
                    "date": r.session.session_date.isoformat() if r.session else None,
                    "remarks": r.remarks,
                }
                for r in rows
            ],
        }
    )


async def _attendance_summary(db, student_id: UUID) -> dict:
    total = await db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(AttendanceRecord.student_id == student_id)
    ) or 0
    present = await db.scalar(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.EXCUSED]),
        )
    ) or 0
    absent = await db.scalar(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == AttendanceStatus.ABSENT,
        )
    ) or 0
    return {"days_present": present, "days_absent": absent, "days_total": total}


async def _ensure_student_access(db, user: User, student: Student) -> None:
    role = user.role.name
    if role in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM, UserRole.INSTRUCTOR, UserRole.ACCOUNTANT}:
        return
    if role == UserRole.STUDENT:
        if student.user_id != user.id:
            raise ForbiddenError("Cannot access another student's data")
        return
    if role == UserRole.PARENT:
        parent = await db.scalar(select(Parent).where(Parent.user_id == user.id))
        if not parent:
            raise ForbiddenError()
        link = await db.scalar(
            select(ParentStudent).where(ParentStudent.parent_id == parent.id, ParentStudent.student_id == student.id)
        )
        if not link:
            raise ForbiddenError("Not linked to this student")
        return
    raise ForbiddenError()


async def _recalc_attendance(db, student_id: UUID) -> None:
    total = await db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(AttendanceRecord.student_id == student_id)
    ) or 0
    if total == 0:
        return
    present = await db.scalar(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.EXCUSED]),
        )
    ) or 0
    student = await db.get(Student, student_id)
    if student:
        student.attendance_pct = round((present / total) * 100, 1)
        if student.attendance_pct < settings.attendance_warning_threshold:
            # Notify student + parents + admins
            if student.user_id:
                await notify_user(
                    db,
                    user_id=student.user_id,
                    title="Attendance Warning",
                    body="Your attendance has fallen below the academy's recommended level.",
                    category="attendance_warning",
                )
        await db.flush()


async def _notify_absence(db, student_id: UUID, session_date: date) -> None:
    student = await db.scalar(
        select(Student).options(selectinload(Student.user)).where(Student.id == student_id)
    )
    if not student:
        return
    name = student.user.full_name if student.user else student.student_code
    body = f"Your child {name} was marked absent today, {session_date.strftime('%d %B %Y')}."

    links = (
        await db.execute(
            select(ParentStudent).options(selectinload(ParentStudent.parent)).where(ParentStudent.student_id == student_id)
        )
    ).scalars().all()
    for link in links:
        if link.parent and link.parent.user_id:
            await notify_user(
                db,
                user_id=link.parent.user_id,
                title="Your child is absent",
                body=body,
                category="attendance_absent",
                channel=NotificationChannel.IN_APP,
                link="/app/parent/attendance",
            )
            # Architecture supports SMS/WhatsApp/Email fan-out via adapters
