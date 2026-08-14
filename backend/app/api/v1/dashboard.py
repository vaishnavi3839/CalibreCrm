from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.response import success
from app.models import (
    AttendanceRecord,
    AttendanceStatus,
    Event,
    Exam,
    FollowUpStatus,
    Lead,
    LeadFollowUp,
    LeadStatus,
    LeadTemperature,
    Meeting,
    Staff,
    StaffPerformanceDaily,
    Student,
    Task,
    TaskStatus,
    User,
    UserRole,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(user: CurrentUser, db: DbSession):
    role = user.role.name
    # Academy pulse uses the local calendar day (staff operate in local time).
    today = date.today()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    if role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return success(await _admin_pulse(db, today, start, end))
    if role == UserRole.RM:
        return success(await _rm_dashboard(db, today, start, end))
    if role == UserRole.TELECALLER:
        return success(await _telecaller_dashboard(db, user, today, start, end))
    if role == UserRole.INSTRUCTOR:
        return success(await _instructor_dashboard(db, user, today))
    if role == UserRole.STUDENT:
        return success(await _student_dashboard(db, user))
    if role == UserRole.PARENT:
        return success(await _parent_dashboard(db, user))
    if role == UserRole.ACCOUNTANT:
        return success(await _accountant_dashboard(db, user, today))
    return success({"role": role.value})


async def _admin_pulse(db, today, start, end) -> dict:
    new_leads = await db.scalar(select(func.count()).select_from(Lead).where(Lead.created_at >= start, Lead.created_at < end)) or 0
    assigned = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.ASSIGNED, Lead.updated_at >= start)
    ) or 0
    hot = await db.scalar(select(func.count()).select_from(Lead).where(Lead.temperature == LeadTemperature.HOT, Lead.is_active.is_(True))) or 0
    warm = await db.scalar(select(func.count()).select_from(Lead).where(Lead.temperature == LeadTemperature.WARM, Lead.is_active.is_(True))) or 0
    cold = await db.scalar(select(func.count()).select_from(Lead).where(Lead.temperature == LeadTemperature.COLD, Lead.is_active.is_(True))) or 0
    pending_fu = await db.scalar(
        select(func.count()).select_from(LeadFollowUp).where(
            LeadFollowUp.status == FollowUpStatus.PENDING,
            LeadFollowUp.scheduled_at >= start,
            LeadFollowUp.scheduled_at < end,
        )
    ) or 0
    registrations = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.REGISTRATION, Lead.updated_at >= start)
    ) or 0
    admissions = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.CONVERTED, Lead.updated_at >= start)
    ) or 0
    present = await db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(
            AttendanceRecord.status == AttendanceStatus.PRESENT,
            AttendanceRecord.created_at >= start,
        )
    ) or 0
    absent = await db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(
            AttendanceRecord.status == AttendanceStatus.ABSENT,
            AttendanceRecord.created_at >= start,
        )
    ) or 0
    upcoming_exams = await db.scalar(select(func.count()).select_from(Exam).where(Exam.exam_date >= today)) or 0
    upcoming_events = await db.scalar(select(func.count()).select_from(Event).where(Event.start_at >= start)) or 0
    meetings = await db.scalar(select(func.count()).select_from(Meeting).where(Meeting.start_at >= start, Meeting.start_at < end + timedelta(days=7))) or 0

    top = (
        await db.execute(
            select(StaffPerformanceDaily)
            .where(StaffPerformanceDaily.performance_date == today)
            .order_by(StaffPerformanceDaily.score.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    top_performer = None
    if top:
        staff = await db.scalar(
            select(Staff).options(selectinload(Staff.user)).where(Staff.id == top.staff_id)
        )
        if staff and staff.user:
            top_performer = {
                "name": staff.user.full_name,
                "photo_url": staff.user.photo_url
                or f"https://api.dicebear.com/7.x/avataaars/svg?seed={staff.user.full_name.replace(' ', '')}&backgroundColor=0a1628",
                "score": top.score,
                "calls": top.calls_completed,
                "admissions": top.admissions,
                "employee_code": staff.employee_code,
            }

    calls = await db.scalar(
        select(func.coalesce(func.sum(StaffPerformanceDaily.calls_completed), 0)).where(
            StaffPerformanceDaily.performance_date == today
        )
    ) or 0

    # Mirror RM dashboard structure so Admin UI can show the same leaderboard layout
    leaderboard = (
        await db.execute(
            select(StaffPerformanceDaily)
            .where(StaffPerformanceDaily.performance_date == today)
            .order_by(StaffPerformanceDaily.score.desc())
            .limit(5)
        )
    ).scalars().all()
    board = []
    for row in leaderboard:
        staff = await db.scalar(
            select(Staff).options(selectinload(Staff.user)).where(Staff.id == row.staff_id)
        )
        name = staff.employee_code if staff else str(row.staff_id)
        photo = None
        if staff and staff.user:
            name = staff.user.full_name
            photo = staff.user.photo_url or (
                f"https://api.dicebear.com/7.x/avataaars/svg?seed={staff.user.full_name.replace(' ', '')}&backgroundColor=0a1628"
            )
        board.append(
            {
                "name": name,
                "photo_url": photo,
                "score": row.score,
                "calls": row.calls_completed,
                "admissions": row.admissions,
            }
        )
    return {
        "role": "admin",
        "title": "Daily Academy Pulse",
        "pulse": {
            "new_leads": new_leads,
            "leads_assigned": assigned,
            "calls_completed": int(calls),
            "hot_leads": hot,
            "warm_leads": warm,
            "cold_leads": cold,
            "pending_followups": pending_fu,
            "registrations": registrations,
            "admissions": admissions,
            "students_present": present,
            "students_absent": absent,
            "upcoming_exams": upcoming_exams,
            "upcoming_events": upcoming_events,
            "staff_meetings": meetings,
            "top_performer": top_performer,
        },
        "leaderboard": board,
    }


async def _rm_dashboard(db, today, start, end) -> dict:
    base = await _admin_pulse(db, today, start, end)
    leaderboard = (
        await db.execute(
            select(StaffPerformanceDaily)
            .where(StaffPerformanceDaily.performance_date == today)
            .order_by(StaffPerformanceDaily.score.desc())
            .limit(5)
        )
    ).scalars().all()
    board = []
    for row in leaderboard:
        staff = await db.scalar(
            select(Staff).options(selectinload(Staff.user)).where(Staff.id == row.staff_id)
        )
        name = staff.employee_code if staff else str(row.staff_id)
        photo = None
        if staff and staff.user:
            name = staff.user.full_name
            photo = staff.user.photo_url or (
                f"https://api.dicebear.com/7.x/avataaars/svg?seed={staff.user.full_name.replace(' ', '')}&backgroundColor=0a1628"
            )
        board.append(
            {
                "name": name,
                "photo_url": photo,
                "score": row.score,
                "calls": row.calls_completed,
                "admissions": row.admissions,
            }
        )
    base["role"] = "rm"
    base["leaderboard"] = board
    if board:
        base["pulse"]["top_performer"] = {
            "name": board[0]["name"],
            "photo_url": board[0]["photo_url"],
            "score": board[0]["score"],
            "calls": board[0]["calls"],
            "admissions": board[0]["admissions"],
        }
    return base


async def _telecaller_dashboard(db, user, today, start, end) -> dict:
    staff = await db.scalar(select(Staff).where(Staff.user_id == user.id))
    if not staff:
        return {"role": "telecaller", "error": "Staff profile missing"}

    my_leads = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.assigned_staff_id == staff.id, Lead.is_active.is_(True))
    ) or 0
    hot = await db.scalar(
        select(func.count()).select_from(Lead).where(
            Lead.assigned_staff_id == staff.id, Lead.temperature == LeadTemperature.HOT, Lead.is_active.is_(True)
        )
    ) or 0
    followups = await db.scalar(
        select(func.count()).select_from(LeadFollowUp).where(
            LeadFollowUp.staff_id == staff.id,
            LeadFollowUp.status == FollowUpStatus.PENDING,
            LeadFollowUp.scheduled_at >= start,
            LeadFollowUp.scheduled_at < end,
        )
    ) or 0
    tasks = await db.scalar(
        select(func.count()).select_from(Task).where(
            Task.assigned_to_id == user.id, Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        )
    ) or 0
    perf = await db.scalar(
        select(StaffPerformanceDaily).where(
            StaffPerformanceDaily.staff_id == staff.id, StaffPerformanceDaily.performance_date == today
        )
    )
    top = (
        await db.execute(
            select(StaffPerformanceDaily)
            .where(StaffPerformanceDaily.performance_date == today)
            .order_by(StaffPerformanceDaily.score.desc())
            .limit(3)
        )
    ).scalars().all()

    top_performers = []
    for i, r in enumerate(top):
        s = await db.scalar(select(Staff).options(selectinload(Staff.user)).where(Staff.id == r.staff_id))
        name = s.user.full_name if s and s.user else str(r.staff_id)
        photo = None
        if s and s.user:
            photo = s.user.photo_url or (
                f"https://api.dicebear.com/7.x/avataaars/svg?seed={s.user.full_name.replace(' ', '')}&backgroundColor=0a1628"
            )
        top_performers.append(
            {
                "rank": i + 1,
                "score": r.score,
                "staff_id": str(r.staff_id),
                "name": name,
                "photo_url": photo,
                "calls": r.calls_completed,
            }
        )

    return {
        "role": "telecaller",
        "greeting": f"Good day, {user.full_name.split()[0]}",
        "stats": {
            "my_leads": my_leads,
            "hot_leads": hot,
            "todays_followups": followups,
            "open_tasks": tasks,
            "calls_today": perf.calls_completed if perf else 0,
            "score_today": perf.score if perf else 0,
        },
        "top_performers": top_performers,
        "top_performer": top_performers[0] if top_performers else None,
        "is_top_performer": bool(top and top[0].staff_id == staff.id),
    }


async def _instructor_dashboard(db, user, today) -> dict:
    from app.services.staff_service import get_top_performer

    staff = await db.scalar(select(Staff).where(Staff.user_id == user.id))
    students = 0
    if staff:
        students = await db.scalar(select(func.count()).select_from(Student).where(Student.instructor_id == staff.id)) or 0
    exams = await db.scalar(select(func.count()).select_from(Exam).where(Exam.exam_date >= today)) or 0
    return {
        "role": "instructor",
        "stats": {"assigned_students": students, "upcoming_exams": exams},
        "top_performer": await get_top_performer(db, today),
    }


async def _accountant_dashboard(db, user, today) -> dict:
    from app.services.staff_service import get_top_performer

    return {
        "role": "accountant",
        "message": "Finance dashboard",
        "widgets": ["payments", "outstanding"],
        "top_performer": await get_top_performer(db, today),
    }


async def _student_dashboard(db, user) -> dict:
    student = await db.scalar(
        select(Student)
        .options(selectinload(Student.course), selectinload(Student.batch))
        .where(Student.user_id == user.id)
    )
    if not student:
        raise NotFoundError("Student profile not found")
    first = user.full_name.split()[0]
    hour = datetime.now().hour
    greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    from app.api.v1.students import _attendance_summary

    summary = await _attendance_summary(db, student.id)
    return {
        "role": "student",
        "greeting": f"{greet}, {first}",
        "student_id": str(student.id),
        "student_code": student.student_code,
        "photo_url": student.photo_url or user.photo_url,
        "course": student.course.name if student.course else None,
        "batch": student.batch.name if student.batch else None,
        "attendance_pct": student.attendance_pct,
        "days_present": summary["days_present"],
        "days_absent": summary["days_absent"],
        "days_total": summary["days_total"],
        "course_progress_pct": student.course_progress_pct,
        "training_hours_completed": student.training_hours_completed,
        # IMPORTANT: no fee/payment fields
    }


async def _parent_dashboard(db, user) -> dict:
    from app.models import Parent, ParentStudent
    from app.api.v1.students import _attendance_summary

    parent = await db.scalar(select(Parent).where(Parent.user_id == user.id))
    if not parent:
        raise NotFoundError("Parent profile not found")
    links = (
        await db.execute(
            select(ParentStudent)
            .options(selectinload(ParentStudent.student).selectinload(Student.user), selectinload(ParentStudent.student).selectinload(Student.course))
            .where(ParentStudent.parent_id == parent.id)
        )
    ).scalars().all()
    children = []
    for link in links:
        s = link.student
        summary = await _attendance_summary(db, s.id)
        children.append(
            {
                "student_id": str(s.id),
                "name": s.user.full_name if s.user else s.student_code,
                "photo_url": s.photo_url or (s.user.photo_url if s.user else None),
                "course": s.course.name if s.course else None,
                "attendance_pct": s.attendance_pct,
                "days_present": summary["days_present"],
                "days_absent": summary["days_absent"],
                "days_total": summary["days_total"],
                "course_progress_pct": s.course_progress_pct,
            }
        )
    return {"role": "parent", "students": children}
