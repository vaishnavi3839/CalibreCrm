from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.core.response import success
from app.models import (
    Announcement,
    AnnouncementType,
    Certificate,
    Course,
    Document,
    Event,
    Exam,
    ExamResult,
    Meeting,
    Notification,
    PerformanceScoreRule,
    Staff,
    StaffPerformanceDaily,
    StaffTarget,
    Student,
    SupportTicket,
    Task,
    TaskPriority,
    TaskStatus,
    TicketCategory,
    TicketStatus,
    User,
    UserRole,
)

router = APIRouter(tags=["ops"])
UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "uploads"
DOCS_DIR = UPLOAD_ROOT / "documents"
CERTS_DIR = UPLOAD_ROOT / "certificates"


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _can_manage_comms(user: User) -> bool:
    return user.role.name in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}


def _can_manage_academy(user: User) -> bool:
    """Courses / student documents — Admin only (not RM)."""
    return user.role.name in {UserRole.SUPER_ADMIN, UserRole.ADMIN}


def _audience_allows(audience: dict, role: str) -> bool:
    roles = (audience or {}).get("roles") or []
    if not roles or "all" in roles:
        return True
    if role in roles:
        return True
    if role in {UserRole.STUDENT.value, "student"} and ("student" in roles or "all_students" in roles):
        return True
    if role in {UserRole.PARENT.value, "parent"} and ("parent" in roles or "parents" in roles):
        return True
    staff_roles = {
        UserRole.SUPER_ADMIN.value,
        UserRole.ADMIN.value,
        UserRole.RM.value,
        UserRole.TELECALLER.value,
        UserRole.INSTRUCTOR.value,
        UserRole.ACCOUNTANT.value,
    }
    if role in staff_roles and "staff" in roles:
        return True
    return False


def _normalize_audience(payload: dict | None) -> dict:
    """Accept audience dict or audience_type shortcut: all|staff|students|parents|students_parents."""
    if not payload:
        return {"roles": ["all"]}
    if payload.get("roles"):
        return {"roles": payload["roles"]}
    kind = (payload.get("audience_type") or payload.get("for") or "all").strip().lower()
    mapping = {
        "all": ["all"],
        "everyone": ["all"],
        "staff": ["staff"],
        "students": ["student"],
        "student": ["student"],
        "parents": ["parent"],
        "parent": ["parent"],
        "students_parents": ["student", "parent"],
        "students_and_parents": ["student", "parent"],
    }
    return {"roles": mapping.get(kind, ["all"])}


async def _user_ids_for_audience(db: DbSession, audience: dict) -> list[UUID]:
    from app.models import Role

    roles = (audience or {}).get("roles") or ["all"]
    stmt = select(User.id).join(Role, User.role_id == Role.id).where(User.is_active.is_(True))
    if "all" not in roles:
        wanted: set[UserRole] = set()
        for r in roles:
            if r == "staff":
                wanted.update(
                    {
                        UserRole.SUPER_ADMIN,
                        UserRole.ADMIN,
                        UserRole.RM,
                        UserRole.TELECALLER,
                        UserRole.INSTRUCTOR,
                        UserRole.ACCOUNTANT,
                    }
                )
            elif r in {"student", "all_students"}:
                wanted.add(UserRole.STUDENT)
            elif r in {"parent", "parents"}:
                wanted.add(UserRole.PARENT)
            else:
                try:
                    wanted.add(UserRole(r))
                except ValueError:
                    continue
        if not wanted:
            return []
        stmt = stmt.where(Role.name.in_(list(wanted)))
    return list((await db.execute(stmt)).scalars().all())


# ─── Tasks ───────────────────────────────────────────────────────────────────


@router.get("/tasks")
async def list_tasks(user: CurrentUser, db: DbSession, status: Optional[TaskStatus] = None):
    filters = []
    if user.role.name in {UserRole.TELECALLER, UserRole.INSTRUCTOR, UserRole.STUDENT, UserRole.PARENT}:
        filters.append(Task.assigned_to_id == user.id)
    if status:
        filters.append(Task.status == status)
    rows = (
        await db.execute(select(Task).where(*filters).order_by(Task.due_at.asc().nullslast()).limit(100))
    ).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "priority": t.priority.value,
                    "status": t.status.value,
                    "due_at": t.due_at.isoformat() if t.due_at else None,
                    "assigned_to_id": str(t.assigned_to_id),
                }
                for t in rows
            ]
        }
    )


@router.post("/tasks")
async def create_task(payload: dict, user: CurrentUser, db: DbSession):
    if user.role.name in {UserRole.STUDENT, UserRole.PARENT}:
        raise ForbiddenError()

    # Telecallers/instructors can create personal tasks; Admin/RM can assign to anyone.
    assigned_raw = payload.get("assigned_to_id")
    if assigned_raw:
        assigned_to_id = UUID(assigned_raw)
        if user.role.name in {UserRole.TELECALLER, UserRole.INSTRUCTOR, UserRole.ACCOUNTANT}:
            if assigned_to_id != user.id:
                raise ForbiddenError("You can only create tasks for yourself")
    else:
        assigned_to_id = user.id

    task = Task(
        title=payload["title"],
        description=payload.get("description"),
        assigned_to_id=assigned_to_id,
        created_by_id=user.id,
        priority=TaskPriority(payload.get("priority", "medium")),
        due_at=_parse_dt(payload["due_at"]) if payload.get("due_at") else None,
        related_lead_id=UUID(payload["related_lead_id"]) if payload.get("related_lead_id") else None,
        related_student_id=UUID(payload["related_student_id"]) if payload.get("related_student_id") else None,
    )
    db.add(task)
    await db.flush()

    if assigned_to_id != user.id:
        from app.services.notification_service import notify_user

        await notify_user(
            db,
            user_id=assigned_to_id,
            title="New task assigned",
            body=f"{user.full_name} assigned you: {task.title}",
            category="task",
            link="/app/tasks" if user.role.name != UserRole.TELECALLER else "/app/telecaller/tasks",
        )

    return success({"id": str(task.id)}, message="Task created", status_code=201)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: UUID, payload: dict, user: CurrentUser, db: DbSession):
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundError("Task not found")
    if task.assigned_to_id != user.id and user.role.name not in {
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.RM,
    }:
        raise ForbiddenError()
    if "status" in payload:
        task.status = TaskStatus(payload["status"])
        if task.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)
        elif task.status != TaskStatus.COMPLETED:
            task.completed_at = None
    if "title" in payload:
        task.title = payload["title"]
    if "description" in payload:
        task.description = payload["description"]
    if "priority" in payload:
        task.priority = TaskPriority(payload["priority"])
    if "due_at" in payload:
        task.due_at = _parse_dt(payload["due_at"]) if payload["due_at"] else None
    if "assigned_to_id" in payload and user.role.name in {
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.RM,
    }:
        task.assigned_to_id = UUID(payload["assigned_to_id"])
    await db.flush()
    return success(message="Task updated")


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: UUID, user: CurrentUser, db: DbSession):
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundError("Task not found")
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        if task.assigned_to_id != user.id and task.created_by_id != user.id:
            raise ForbiddenError()
    await db.delete(task)
    await db.flush()
    return success(message="Task deleted")


# ─── Performance / Leaderboard ───────────────────────────────────────────────


@router.get("/staff/leaderboard")
async def leaderboard(
    user: CurrentUser,
    db: DbSession,
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
):
    today = date.today()
    if period == "daily":
        start = today
    elif period == "weekly":
        start = today - timedelta(days=today.weekday())
    else:
        start = today.replace(day=1)

    rows = (
        await db.execute(
            select(
                StaffPerformanceDaily.staff_id,
                func.sum(StaffPerformanceDaily.score).label("score"),
                func.sum(StaffPerformanceDaily.calls_completed).label("calls"),
                func.sum(StaffPerformanceDaily.admissions).label("admissions"),
                func.sum(StaffPerformanceDaily.followups_completed).label("followups"),
            )
            .where(StaffPerformanceDaily.performance_date >= start)
            .group_by(StaffPerformanceDaily.staff_id)
            .order_by(func.sum(StaffPerformanceDaily.score).desc())
            .limit(10)
        )
    ).all()

    items = []
    for i, row in enumerate(rows):
        staff = await db.scalar(select(Staff).options(selectinload(Staff.user)).where(Staff.id == row.staff_id))
        badges = []
        if i == 0:
            badges.append("Top Performer")
        if row.admissions and row.admissions >= 2:
            badges.append("Conversion Champion")
        if row.calls and row.calls >= 40:
            badges.append("Calling Champion")
        if row.followups and row.followups >= 10:
            badges.append("Follow-up Master")
        items.append(
            {
                "rank": i + 1,
                "staff_id": str(row.staff_id),
                "name": staff.user.full_name if staff and staff.user else str(row.staff_id),
                "score": int(row.score or 0),
                "calls": int(row.calls or 0),
                "admissions": int(row.admissions or 0),
                "badges": badges,
            }
        )
    return success({"period": period, "items": items})


@router.get("/staff/performance")
async def my_performance(user: CurrentUser, db: DbSession):
    staff = await db.scalar(select(Staff).where(Staff.user_id == user.id))
    if not staff and user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()

    staff_id = staff.id if staff else None
    if not staff_id:
        return success({"message": "Select a staff member", "items": []})

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    targets = (
        await db.execute(
            select(StaffTarget).where(StaffTarget.staff_id == staff_id, StaffTarget.period_end >= today)
        )
    ).scalars().all()
    perf = await db.scalar(
        select(StaffPerformanceDaily).where(
            StaffPerformanceDaily.staff_id == staff_id, StaffPerformanceDaily.performance_date == today
        )
    )
    return success(
        {
            "today": {
                "calls": perf.calls_completed if perf else 0,
                "followups": perf.followups_completed if perf else 0,
                "hot_leads": perf.hot_leads if perf else 0,
                "score": perf.score if perf else 0,
            },
            "targets": [
                {
                    "metric": t.metric_key,
                    "period": t.period_type,
                    "target": t.target_value,
                    "current": t.current_value,
                }
                for t in targets
            ],
        }
    )


# ─── Notifications ───────────────────────────────────────────────────────────


@router.get("/notifications")
async def list_notifications(user: CurrentUser, db: DbSession, unread_only: bool = False):
    filters = [Notification.user_id == user.id]
    if unread_only:
        filters.append(Notification.is_read.is_(False))
    rows = (
        await db.execute(
            select(Notification).where(*filters).order_by(Notification.created_at.desc()).limit(50)
        )
    ).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "body": n.body,
                    "category": n.category,
                    "is_read": n.is_read,
                    "link": n.link,
                    "created_at": n.created_at.isoformat(),
                }
                for n in rows
            ]
        }
    )


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: UUID, user: CurrentUser, db: DbSession):
    n = await db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise NotFoundError()
    n.is_read = True
    n.read_at = datetime.now(timezone.utc)
    await db.flush()
    return success(message="Marked as read")


# ─── Courses / Announcements / Events ────────────────────────────────────────


@router.get("/courses")
async def list_courses(db: DbSession, user: CurrentUser, include_inactive: bool = False):
    filters = []
    if not include_inactive or not _can_manage_academy(user):
        filters.append(Course.is_active.is_(True))
    rows = (await db.execute(select(Course).where(*filters).order_by(Course.name))).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(c.id),
                    "code": c.code,
                    "name": c.name,
                    "description": c.description,
                    "duration_months": c.duration_months,
                    "has_flight_training": c.has_flight_training,
                    "is_active": c.is_active,
                }
                for c in rows
            ]
        }
    )


@router.post("/courses")
async def create_course(payload: dict, user: CurrentUser, db: DbSession):
    if not _can_manage_academy(user):
        raise ForbiddenError("Only Admin can manage courses")
    code = (payload.get("code") or "").strip().upper()
    name = (payload.get("name") or "").strip()
    if not code or not name:
        raise ValidationAppError("code and name are required")
    existing = await db.scalar(select(Course).where(Course.code == code))
    if existing:
        raise ValidationAppError("Course code already exists")
    course = Course(
        code=code,
        name=name,
        description=payload.get("description"),
        duration_months=payload.get("duration_months"),
        has_flight_training=bool(payload.get("has_flight_training", False)),
        required_flight_hours=payload.get("required_flight_hours"),
        required_simulator_hours=payload.get("required_simulator_hours"),
    )
    db.add(course)
    await db.flush()
    return success(
        {"id": str(course.id), "code": course.code, "name": course.name},
        message="Course created",
        status_code=201,
    )


@router.delete("/courses/{course_id}")
async def delete_course(course_id: UUID, user: CurrentUser, db: DbSession):
    if not _can_manage_academy(user):
        raise ForbiddenError("Only Admin can manage courses")
    course = await db.get(Course, course_id)
    if not course:
        raise NotFoundError("Course not found")
    course.is_active = False
    await db.flush()
    return success(message="Course deleted")


@router.get("/announcements")
async def list_announcements(user: CurrentUser, db: DbSession):
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(Announcement)
            .where(Announcement.is_published.is_(True), Announcement.publish_at <= now)
            .order_by(Announcement.publish_at.desc())
            .limit(50)
        )
    ).scalars().all()
    role = user.role.name.value
    items = []
    for a in rows:
        if a.expire_at and a.expire_at < now:
            continue
        if not _audience_allows(a.audience or {}, role):
            continue
        items.append(
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "type": a.announcement_type.value,
                "event_date": a.event_date.isoformat() if a.event_date else None,
                "location": a.location,
                "publish_at": a.publish_at.isoformat() if a.publish_at else None,
            }
        )
    return success({"items": items})


@router.post("/announcements")
async def create_announcement(payload: dict, user: CurrentUser, db: DbSession):
    if not _can_manage_comms(user):
        raise ForbiddenError("Only Admin/RM can create notices")
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    if not title or not description:
        raise ValidationAppError("title and description are required")
    ann = Announcement(
        title=title,
        description=description,
        announcement_type=AnnouncementType(payload.get("type") or payload.get("announcement_type") or "general"),
        event_date=date.fromisoformat(payload["event_date"]) if payload.get("event_date") else None,
        location=payload.get("location"),
        audience=_normalize_audience(
            payload.get("audience")
            if isinstance(payload.get("audience"), dict)
            else {"audience_type": payload.get("audience_type", "all")}
        ),
        publish_at=_parse_dt(payload.get("publish_at")) or datetime.now(timezone.utc),
        expire_at=_parse_dt(payload.get("expire_at")),
        created_by_id=user.id,
        is_published=payload.get("is_published", True),
    )
    db.add(ann)
    await db.flush()

    from app.services.notification_service import notify_users

    recipient_ids = await _user_ids_for_audience(db, ann.audience)
    recipient_ids = [uid for uid in recipient_ids if uid != user.id]
    if recipient_ids:
        await notify_users(
            db,
            user_ids=recipient_ids,
            title="New notice",
            body=ann.title,
            category="announcement",
            link="/app/announcements",
        )

    return success(
        {"id": str(ann.id), "title": ann.title, "type": ann.announcement_type.value},
        message="Notice published",
        status_code=201,
    )


@router.patch("/announcements/{announcement_id}")
async def update_announcement(announcement_id: UUID, payload: dict, user: CurrentUser, db: DbSession):
    if not _can_manage_comms(user):
        raise ForbiddenError()
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise NotFoundError("Notice not found")
    if "title" in payload:
        ann.title = payload["title"].strip()
    if "description" in payload:
        ann.description = payload["description"].strip()
    if "type" in payload or "announcement_type" in payload:
        ann.announcement_type = AnnouncementType(payload.get("type") or payload["announcement_type"])
    if "location" in payload:
        ann.location = payload["location"]
    if "event_date" in payload:
        ann.event_date = date.fromisoformat(payload["event_date"]) if payload["event_date"] else None
    if "audience" in payload or "audience_type" in payload:
        ann.audience = _normalize_audience(
            payload.get("audience")
            if isinstance(payload.get("audience"), dict)
            else {"audience_type": payload.get("audience_type", "all")}
        )
    if "is_published" in payload:
        ann.is_published = bool(payload["is_published"])
    if "expire_at" in payload:
        ann.expire_at = _parse_dt(payload["expire_at"])
    await db.flush()
    return success(message="Notice updated")


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: UUID, user: CurrentUser, db: DbSession):
    if not _can_manage_comms(user):
        raise ForbiddenError()
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise NotFoundError("Notice not found")
    await db.delete(ann)
    await db.flush()
    return success(message="Notice deleted")


@router.get("/events")
async def list_events(user: CurrentUser, db: DbSession):
    rows = (
        await db.execute(select(Event).where(Event.start_at >= datetime.now(timezone.utc) - timedelta(days=1)).order_by(Event.start_at).limit(50))
    ).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "description": e.description,
                    "event_type": e.event_type,
                    "start_at": e.start_at.isoformat(),
                    "end_at": e.end_at.isoformat() if e.end_at else None,
                    "location": e.location,
                }
                for e in rows
            ]
        }
    )


@router.post("/events")
async def create_event(payload: dict, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError("Only Admin/RM can create events")
    if not payload.get("title") or not payload.get("start_at"):
        from app.core.exceptions import ValidationAppError

        raise ValidationAppError("title and start_at are required")

    start_at = datetime.fromisoformat(payload["start_at"].replace("Z", "+00:00"))
    end_at = None
    if payload.get("end_at"):
        end_at = datetime.fromisoformat(payload["end_at"].replace("Z", "+00:00"))

    event = Event(
        title=payload["title"].strip(),
        description=payload.get("description"),
        event_type=payload.get("event_type") or "general",
        start_at=start_at,
        end_at=end_at,
        location=payload.get("location"),
        audience=payload.get("audience") or {"roles": ["all"]},
        created_by_id=user.id,
    )
    db.add(event)
    await db.flush()
    return success(
        {
            "id": str(event.id),
            "title": event.title,
            "event_type": event.event_type,
            "start_at": event.start_at.isoformat(),
            "location": event.location,
        },
        message="Event created",
        status_code=201,
    )


@router.get("/meetings")
async def list_meetings(user: CurrentUser, db: DbSession):
    rows = (
        await db.execute(
            select(Meeting)
            .where(Meeting.start_at >= datetime.now(timezone.utc) - timedelta(hours=1))
            .order_by(Meeting.start_at)
            .limit(50)
        )
    ).scalars().all()
    role = user.role.name.value
    items = []
    for m in rows:
        if not _audience_allows(m.audience or {"roles": ["all"]}, role):
            continue
        items.append(
            {
                "id": str(m.id),
                "title": m.title,
                "description": m.description,
                "start_at": m.start_at.isoformat(),
                "duration_minutes": m.duration_minutes,
                "zoom_link": m.zoom_link,
                "agenda": m.agenda,
                "audience": m.audience or {"roles": ["all"]},
            }
        )
    return success({"items": items})


@router.post("/meetings")
async def create_meeting(payload: dict, user: CurrentUser, db: DbSession):
    if not _can_manage_comms(user):
        raise ForbiddenError("Only Admin/RM can schedule meetings")
    title = (payload.get("title") or "").strip()
    if not title or not payload.get("start_at"):
        raise ValidationAppError("title and start_at are required")
    audience = _normalize_audience(
        payload.get("audience")
        if isinstance(payload.get("audience"), dict)
        else {"audience_type": payload.get("audience_type", "all")}
    )
    meeting = Meeting(
        title=title,
        description=payload.get("description"),
        agenda=payload.get("agenda"),
        start_at=_parse_dt(payload["start_at"]),
        duration_minutes=int(payload.get("duration_minutes") or 60),
        zoom_link=payload.get("zoom_link") or payload.get("join_link"),
        audience=audience,
        created_by_id=user.id,
    )
    db.add(meeting)
    await db.flush()

    from app.services.notification_service import notify_users

    when = meeting.start_at.strftime("%d %b %Y, %I:%M %p")
    body = f"{meeting.title} on {when}"
    if meeting.zoom_link:
        body += " — join link available in Meetings"
    recipient_ids = [uid for uid in await _user_ids_for_audience(db, audience) if uid != user.id]
    if recipient_ids:
        await notify_users(
            db,
            user_ids=recipient_ids,
            title="Meeting scheduled",
            body=body,
            category="meeting",
            link="/app/meetings",
        )

    return success(
        {
            "id": str(meeting.id),
            "title": meeting.title,
            "start_at": meeting.start_at.isoformat(),
            "zoom_link": meeting.zoom_link,
            "audience": meeting.audience,
        },
        message="Meeting scheduled",
        status_code=201,
    )


@router.patch("/meetings/{meeting_id}")
async def update_meeting(meeting_id: UUID, payload: dict, user: CurrentUser, db: DbSession):
    if not _can_manage_comms(user):
        raise ForbiddenError()
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise NotFoundError("Meeting not found")
    if "title" in payload:
        meeting.title = payload["title"].strip()
    if "description" in payload:
        meeting.description = payload["description"]
    if "agenda" in payload:
        meeting.agenda = payload["agenda"]
    if "start_at" in payload and payload["start_at"]:
        meeting.start_at = _parse_dt(payload["start_at"])
    if "duration_minutes" in payload:
        meeting.duration_minutes = int(payload["duration_minutes"])
    if "zoom_link" in payload or "join_link" in payload:
        meeting.zoom_link = payload.get("zoom_link") or payload.get("join_link")
    if "audience" in payload or "audience_type" in payload:
        meeting.audience = _normalize_audience(
            payload.get("audience")
            if isinstance(payload.get("audience"), dict)
            else {"audience_type": payload.get("audience_type", "all")}
        )
    await db.flush()
    return success(message="Meeting updated")


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: UUID, user: CurrentUser, db: DbSession):
    if not _can_manage_comms(user):
        raise ForbiddenError()
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise NotFoundError("Meeting not found")
    await db.delete(meeting)
    await db.flush()
    return success(message="Meeting deleted")


# ─── Student documents & certificates ────────────────────────────────────────


@router.get("/students/{student_id}/documents")
async def list_student_documents(student_id: UUID, user: CurrentUser, db: DbSession):
    student = await db.get(Student, student_id)
    if not student:
        raise NotFoundError("Student not found")
    await _ensure_doc_access(db, user, student)
    rows = (
        await db.execute(select(Document).where(Document.student_id == student_id).order_by(Document.created_at.desc()))
    ).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(d.id),
                    "title": d.title,
                    "document_type": d.document_type,
                    "file_name": d.file_name,
                    "file_url": d.file_key,
                    "mime_type": d.mime_type,
                    "can_download": (
                        (user.role.name == UserRole.STUDENT and d.can_student_download)
                        or (user.role.name == UserRole.PARENT and d.can_parent_download)
                        or user.role.name
                        in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM, UserRole.INSTRUCTOR}
                    ),
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in rows
            ]
        }
    )


@router.post("/students/{student_id}/documents")
async def upload_student_document(
    student_id: UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form("general"),
):
    if not _can_manage_academy(user):
        raise ForbiddenError("Only Admin can upload student documents")
    student = await db.get(Student, student_id)
    if not student:
        raise NotFoundError("Student not found")
    raw = await file.read()
    if not raw:
        raise ValidationAppError("Empty file")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file.bin").suffix or ".bin"
    filename = f"{student_id}_{uuid4().hex}{ext}"
    path = DOCS_DIR / filename
    path.write_bytes(raw)
    file_url = f"/uploads/documents/{filename}"
    doc = Document(
        title=title.strip(),
        document_type=document_type.strip() or "general",
        student_id=student_id,
        file_key=file_url,
        file_name=file.filename or filename,
        mime_type=file.content_type,
        file_size=len(raw),
        uploaded_by_id=user.id,
        can_student_download=True,
        can_parent_download=True,
    )
    db.add(doc)
    await db.flush()

    if student.user_id:
        from app.services.notification_service import notify_user

        await notify_user(
            db,
            user_id=student.user_id,
            title="New document uploaded",
            body=f"{title.strip()} is available in your Documents.",
            category="document",
            link="/app/student/documents",
        )

    return success(
        {"id": str(doc.id), "title": doc.title, "file_url": file_url},
        message="Document uploaded",
        status_code=201,
    )


@router.delete("/documents/{document_id}")
async def delete_document(document_id: UUID, user: CurrentUser, db: DbSession):
    if not _can_manage_academy(user):
        raise ForbiddenError("Only Admin can delete documents")
    doc = await db.get(Document, document_id)
    if not doc:
        raise NotFoundError("Document not found")
    await db.delete(doc)
    await db.flush()
    return success(message="Document deleted")


@router.get("/students/{student_id}/certificates")
async def list_student_certificates(student_id: UUID, user: CurrentUser, db: DbSession):
    student = await db.get(Student, student_id)
    if not student:
        raise NotFoundError("Student not found")
    await _ensure_doc_access(db, user, student)
    rows = (
        await db.execute(
            select(Certificate)
            .options(selectinload(Certificate.course))
            .where(Certificate.student_id == student_id)
            .order_by(Certificate.completion_date.desc())
        )
    ).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(c.id),
                    "certificate_code": c.certificate_code,
                    "title": c.title,
                    "course": c.course.name if c.course else None,
                    "completion_date": c.completion_date.isoformat(),
                    "file_url": c.file_key,
                    "verify_url": f"/verify/{c.certificate_code}",
                    "is_verified": c.is_verified,
                }
                for c in rows
            ]
        }
    )


@router.post("/students/{student_id}/certificates")
async def issue_certificate(
    student_id: UUID,
    user: CurrentUser,
    db: DbSession,
    title: str = Form(...),
    course_id: str = Form(...),
    completion_date: str = Form(...),
    file: UploadFile | None = File(None),
):
    if not _can_manage_academy(user):
        raise ForbiddenError("Only Admin can issue certificates")
    student = await db.get(Student, student_id)
    if not student:
        raise NotFoundError("Student not found")
    course = await db.get(Course, UUID(course_id))
    if not course:
        raise NotFoundError("Course not found")

    count = await db.scalar(select(func.count()).select_from(Certificate)) or 0
    code = f"CAA-{course.code}-{date.today().year}-{count + 1:05d}"
    file_url = None
    if file and file.filename:
        raw = await file.read()
        CERTS_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename).suffix or ".pdf"
        filename = f"{code.replace('/', '-')}{ext}"
        (CERTS_DIR / filename).write_bytes(raw)
        file_url = f"/uploads/certificates/{filename}"

    cert = Certificate(
        certificate_code=code,
        student_id=student_id,
        course_id=course.id,
        title=title.strip(),
        completion_date=date.fromisoformat(completion_date),
        file_key=file_url,
        qr_payload=f"https://calibre.academy/verify/{code}",
        is_verified=True,
        issued_by_id=user.id,
    )
    db.add(cert)
    await db.flush()

    if student.user_id:
        from app.services.notification_service import notify_user

        await notify_user(
            db,
            user_id=student.user_id,
            title="New certificate issued",
            body=f"{title.strip()} is now available in your Documents.",
            category="certificate",
            link="/app/student/documents",
        )

    return success(
        {"id": str(cert.id), "certificate_code": code, "verify_url": f"/verify/{code}", "file_url": file_url},
        message="Certificate issued",
        status_code=201,
    )


@router.delete("/certificates/{certificate_id}")
async def delete_certificate(certificate_id: UUID, user: CurrentUser, db: DbSession):
    if not _can_manage_academy(user):
        raise ForbiddenError("Only Admin can delete certificates")
    cert = await db.get(Certificate, certificate_id)
    if not cert:
        raise NotFoundError("Certificate not found")
    await db.delete(cert)
    await db.flush()
    return success(message="Certificate deleted")


async def _ensure_doc_access(db, user: User, student: Student) -> None:
    role = user.role.name
    if role in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM, UserRole.INSTRUCTOR}:
        return
    if role == UserRole.STUDENT and student.user_id == user.id:
        return
    if role == UserRole.PARENT:
        from app.models import Parent, ParentStudent

        parent = await db.scalar(select(Parent).where(Parent.user_id == user.id))
        if parent:
            link = await db.scalar(
                select(ParentStudent).where(
                    ParentStudent.parent_id == parent.id, ParentStudent.student_id == student.id
                )
            )
            if link:
                return
    raise ForbiddenError()


# ─── Certificates (public verify) ────────────────────────────────────────────


@router.get("/certificates/verify/{certificate_code}")
async def verify_certificate(certificate_code: str, db: DbSession):
    cert = await db.scalar(
        select(Certificate)
        .options(
            selectinload(Certificate.student).selectinload(Student.user),
            selectinload(Certificate.course),
        )
        .where(Certificate.certificate_code == certificate_code)
    )

    if not cert or not cert.is_verified:
        return success({"status": "invalid", "verified": False}, message="Certificate not found")
    return success(
        {
            "status": "verified",
            "verified": True,
            "certificate_id": cert.certificate_code,
            "student_name": cert.student.user.full_name if cert.student and cert.student.user else None,
            "course": cert.course.name if cert.course else None,
            "completion_date": cert.completion_date.isoformat(),
        }
    )


@router.get("/exams")
async def list_exams(user: CurrentUser, db: DbSession):
    rows = (await db.execute(select(Exam).order_by(Exam.exam_date.desc()).limit(50))).scalars().all()
    return success(
        {
            "items": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "exam_date": e.exam_date.isoformat(),
                    "venue": e.venue,
                    "max_marks": e.max_marks,
                }
                for e in rows
            ]
        }
    )


@router.post("/support-tickets")
async def create_ticket(payload: dict, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.STUDENT, UserRole.PARENT}:
        raise ForbiddenError("Only students/parents can create support tickets here")
    count = await db.scalar(select(func.count()).select_from(SupportTicket)) or 0
    ticket = SupportTicket(
        ticket_code=f"TKT-{date.today().year}-{count + 1:05d}",
        created_by_id=user.id,
        category=TicketCategory(payload.get("category", "general")),
        subject=payload["subject"],
        description=payload["description"],
        priority=TaskPriority(payload.get("priority", "medium")),
    )
    if user.role.name == UserRole.STUDENT:
        st = await db.scalar(select(Student).where(Student.user_id == user.id))
        if st:
            ticket.student_id = st.id
    db.add(ticket)
    await db.flush()
    return success({"id": str(ticket.id), "ticket_code": ticket.ticket_code}, status_code=201)


@router.get("/reports/conversion-funnel")
async def conversion_funnel(user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    from app.models import Lead, LeadStatus

    stages = [
        LeadStatus.NEW,
        LeadStatus.CONTACTED,
        LeadStatus.INTERESTED,
        LeadStatus.COUNSELLING,
        LeadStatus.CAMPUS_VISIT,
        LeadStatus.REGISTRATION,
        LeadStatus.CONVERTED,
    ]
    # Funnel counts are cumulative-ish: count leads that reached at least each stage
    # For simplicity, count by exact status + later statuses
    order = {s: i for i, s in enumerate(stages)}
    all_leads = (await db.execute(select(Lead.status))).scalars().all()
    counts = {s.value: 0 for s in stages}
    for st in all_leads:
        if st in order:
            for s, idx in order.items():
                if order[st] >= idx:
                    counts[s.value] += 1
        # also map assigned/follow_up into early stages loosely
        elif st in {LeadStatus.ASSIGNED, LeadStatus.FOLLOW_UP}:
            counts[LeadStatus.NEW.value] += 1
            counts[LeadStatus.CONTACTED.value] += 1

    total = max(counts[LeadStatus.NEW.value], 1)
    funnel = []
    for s in stages:
        c = counts[s.value]
        funnel.append({"stage": s.value, "count": c, "conversion_pct": round(c / total * 100, 1)})
    return success({"funnel": funnel})


@router.get("/reports/lead-sources")
async def lead_source_report(user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    from app.models import Lead, LeadSource, LeadStatus

    items = []
    for src in LeadSource:
        total = await db.scalar(select(func.count()).select_from(Lead).where(Lead.source == src)) or 0
        admissions = await db.scalar(
            select(func.count()).select_from(Lead).where(Lead.source == src, Lead.status == LeadStatus.CONVERTED)
        ) or 0
        items.append(
            {
                "source": src.value,
                "leads": total,
                "admissions": admissions,
                "conversion_pct": round((admissions / total * 100), 1) if total else 0,
            }
        )
    items.sort(key=lambda x: x["leads"], reverse=True)
    return success({"items": items})
