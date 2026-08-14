"""QR punch, GPS geofence, grooming selfie, late penalties, and salary slips."""

from __future__ import annotations

import io
import math
import secrets
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError, ValidationAppError
from app.models import (
    AcademyPunchQr,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    Branch,
    DeductionType,
    LateWarning,
    MonthlySalarySlip,
    ParentStudent,
    PayrollDeduction,
    PunchEvent,
    PunchType,
    Staff,
    Student,
    SystemConfig,
    User,
    UserRole,
)
from app.services.grooming_service import analyze_grooming, grooming_ai_status
from app.services.notification_service import notify_user

PUNCH_SETTINGS_KEY = "academy_punch_settings"
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "punches"
IST = timezone(__import__("datetime").timedelta(hours=5, minutes=30))

DEFAULT_SETTINGS = {
    "staff_start": "09:00",
    "staff_end": "18:00",
    "student_start": "09:00",
    "student_end": "17:00",
    "late_grace_minutes": 15,
    "staff_late_warnings_for_half_day": 3,
    "staff_warnings_for_half_salary": 7,
    "grooming_fine": 500,
    "working_days_per_month": 26,
    "academy_lat": 28.6139,
    "academy_lng": 77.2090,
    "geofence_radius_m": 200,
    "require_selfie": True,
    "require_gps_for_staff": True,
}


def _parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _ist_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(IST)


def _ist_today() -> date:
    return _ist_now().date()


async def _sync_student_attendance_from_punch(
    db: AsyncSession,
    *,
    student: Student,
    punch: PunchEvent,
) -> Optional[str]:
    """Mirror QR IN punch into AttendanceRecord so student/parent pages show present/late."""
    if not student.batch_id:
        return None

    status = AttendanceStatus.LATE if punch.is_late else AttendanceStatus.PRESENT
    remarks = (
        f"QR punch IN late +{punch.late_minutes}m"
        if punch.is_late
        else "QR punch IN"
    )

    session = await db.scalar(
        select(AttendanceSession)
        .where(
            AttendanceSession.batch_id == student.batch_id,
            AttendanceSession.session_date == punch.punch_date,
        )
        .order_by(AttendanceSession.created_at.desc())
        .limit(1)
    )
    if not session:
        session = AttendanceSession(
            batch_id=student.batch_id,
            subject_id=None,
            session_date=punch.punch_date,
            notes="Auto-created from QR punch",
        )
        db.add(session)
        await db.flush()

    record = await db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == student.id,
        )
    )
    if record:
        if record.status == AttendanceStatus.EXCUSED:
            return "Attendance already excused"
        record.status = status
        record.remarks = remarks
    else:
        day_records = (
            await db.execute(
                select(AttendanceRecord)
                .join(AttendanceSession)
                .where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceSession.session_date == punch.punch_date,
                )
            )
        ).scalars().all()
        if day_records:
            for r in day_records:
                if r.status != AttendanceStatus.EXCUSED:
                    r.status = status
                    r.remarks = remarks
        else:
            db.add(
                AttendanceRecord(
                    session_id=session.id,
                    student_id=student.id,
                    status=status,
                    remarks=remarks,
                )
            )

    await db.flush()

    total = int(
        await db.scalar(
            select(func.count()).select_from(AttendanceRecord).where(AttendanceRecord.student_id == student.id)
        )
        or 0
    )
    present = int(
        await db.scalar(
            select(func.count())
            .select_from(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.status.in_(
                    [AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.EXCUSED]
                ),
            )
        )
        or 0
    )
    if total > 0:
        student.attendance_pct = round(100.0 * present / total, 1)

    return f"Attendance marked {status.value}"


async def get_punch_settings(db: AsyncSession) -> dict:
    row = await db.scalar(select(SystemConfig).where(SystemConfig.key == PUNCH_SETTINGS_KEY))
    if not row:
        row = SystemConfig(
            key=PUNCH_SETTINGS_KEY,
            value=dict(DEFAULT_SETTINGS),
            description="Academy QR punch, GPS geofence, late and salary rules",
        )
        db.add(row)
        await db.flush()
        merged = dict(DEFAULT_SETTINGS)
    else:
        merged = dict(DEFAULT_SETTINGS)
        merged.update(row.value or {})
    ai = grooming_ai_status()
    merged["grooming_ai_ready"] = ai["ready"]
    merged["grooming_ai_provider"] = ai["provider"]
    merged["grooming_ai_model"] = ai["model"]
    return merged


async def save_punch_settings(db: AsyncSession, *, updates: dict, actor: User) -> dict:
    if actor.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError("Only Admin can update punch settings")
    current = await get_punch_settings(db)
    current.update({k: v for k, v in updates.items() if k in DEFAULT_SETTINGS})
    row = await db.scalar(select(SystemConfig).where(SystemConfig.key == PUNCH_SETTINGS_KEY))
    if not row:
        row = SystemConfig(key=PUNCH_SETTINGS_KEY, value=current)
        db.add(row)
    else:
        row.value = current
    await db.flush()
    return current


async def get_or_create_active_qr(db: AsyncSession) -> AcademyPunchQr:
    qr = await db.scalar(
        select(AcademyPunchQr).where(AcademyPunchQr.is_active.is_(True)).order_by(AcademyPunchQr.created_at.desc())
    )
    if qr:
        return qr
    qr = AcademyPunchQr(token=secrets.token_urlsafe(24), label="Academy Punch", is_active=True)
    db.add(qr)
    await db.flush()
    return qr


async def rotate_punch_qr(db: AsyncSession, *, actor: User) -> AcademyPunchQr:
    if actor.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError("Only Admin can rotate punch QR")
    existing = (
        await db.execute(select(AcademyPunchQr).where(AcademyPunchQr.is_active.is_(True)))
    ).scalars().all()
    for row in existing:
        row.is_active = False
    qr = AcademyPunchQr(token=secrets.token_urlsafe(24), label="Academy Punch", is_active=True)
    db.add(qr)
    await db.flush()
    return qr


def save_selfie(user_id: UUID, image_bytes: bytes) -> str:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    name = f"{user_id}_{int(datetime.now(timezone.utc).timestamp())}.jpg"
    path = UPLOAD_ROOT / name
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((1280, 1280))
    img.save(path, format="JPEG", quality=85)
    return f"/uploads/punches/{name}"


async def _month_warning_count(db: AsyncSession, user_id: UUID, month_key: str) -> int:
    return int(
        await db.scalar(
            select(func.count()).select_from(LateWarning).where(
                LateWarning.user_id == user_id, LateWarning.month_key == month_key
            )
        )
        or 0
    )


async def _has_deduction(
    db: AsyncSession, staff_id: UUID, month_key: str, dtype: DeductionType
) -> bool:
    return bool(
        await db.scalar(
            select(PayrollDeduction.id).where(
                PayrollDeduction.staff_id == staff_id,
                PayrollDeduction.month_key == month_key,
                PayrollDeduction.deduction_type == dtype,
            ).limit(1)
        )
    )


async def _apply_staff_late_penalties(
    db: AsyncSession,
    *,
    staff: Staff,
    user: User,
    punch: PunchEvent,
    settings: dict,
) -> list[str]:
    notes: list[str] = []
    month_key = punch.punch_date.strftime("%Y-%m")
    existing = await db.scalar(
        select(LateWarning).where(
            LateWarning.user_id == user.id, LateWarning.warning_date == punch.punch_date
        )
    )
    if existing:
        return notes

    warning = LateWarning(
        user_id=user.id,
        warning_date=punch.punch_date,
        month_key=month_key,
        punch_event_id=punch.id,
        note=f"Late by {punch.late_minutes} minutes",
    )
    db.add(warning)
    await db.flush()
    notes.append("Late warning recorded")

    count = await _month_warning_count(db, user.id, month_key)
    threshold_half_day = int(settings["staff_late_warnings_for_half_day"])
    threshold_half_salary = int(settings["staff_warnings_for_half_salary"])
    salary = float(staff.monthly_salary or 0)
    working_days = max(1, int(settings["working_days_per_month"]))
    daily = salary / working_days

    if count >= threshold_half_day and not await _has_deduction(
        db, staff.id, month_key, DeductionType.HALF_DAY
    ):
        amount = round(daily / 2, 2)
        db.add(
            PayrollDeduction(
                staff_id=staff.id,
                month_key=month_key,
                deduction_type=DeductionType.HALF_DAY,
                amount=amount,
                reason=f"Half-day salary cut after {threshold_half_day} late warnings",
                punch_event_id=punch.id,
            )
        )
        notes.append(f"Half-day deduction ₹{amount}")

    if count >= threshold_half_salary and not await _has_deduction(
        db, staff.id, month_key, DeductionType.HALF_SALARY
    ):
        amount = round(salary / 2, 2)
        db.add(
            PayrollDeduction(
                staff_id=staff.id,
                month_key=month_key,
                deduction_type=DeductionType.HALF_SALARY,
                amount=amount,
                reason=f"Half salary cut after {threshold_half_salary} late warnings",
                punch_event_id=punch.id,
            )
        )
        notes.append(f"Half-salary deduction ₹{amount}")

    await notify_user(
        db,
        user_id=user.id,
        title="Late punch warning",
        body=f"You punched in late by {punch.late_minutes} min. Warnings this month: {count}.",
        category="punch_late",
        link="/app/punch",
    )
    return notes


async def _apply_student_late(
    db: AsyncSession, *, student: Student, user: User, punch: PunchEvent
) -> list[str]:
    notes: list[str] = []
    if student.training_days_remaining > 0:
        student.training_days_remaining = max(0, student.training_days_remaining - 1)
        notes.append(
            f"1 training day cut (remaining {student.training_days_remaining}/{student.training_days_total})"
        )

    await notify_user(
        db,
        user_id=user.id,
        title="Late punch — training day cut",
        body=f"Late by {punch.late_minutes} min. Training days left: {student.training_days_remaining}.",
        category="punch_late",
        link="/app/punch",
    )

    from app.models import Parent

    parent_rows = (
        await db.execute(
            select(ParentStudent)
            .options(selectinload(ParentStudent.parent).selectinload(Parent.user))
            .where(ParentStudent.student_id == student.id)
        )
    ).scalars().all()
    for link in parent_rows:
        if link.parent and link.parent.user_id:
            await notify_user(
                db,
                user_id=link.parent.user_id,
                title="Your child punched in late",
                body=f"{user.full_name} was late by {punch.late_minutes} minutes today. "
                f"Training days remaining: {student.training_days_remaining}.",
                category="punch_late",
                link="/app/parent/attendance",
            )
    return notes


async def _apply_grooming_fine(
    db: AsyncSession,
    *,
    user: User,
    staff: Optional[Staff],
    student: Optional[Student],
    punch: PunchEvent,
    settings: dict,
) -> Optional[str]:
    fine = float(settings["grooming_fine"])
    month_key = punch.punch_date.strftime("%Y-%m")
    if staff:
        db.add(
            PayrollDeduction(
                staff_id=staff.id,
                month_key=month_key,
                deduction_type=DeductionType.GROOMING_FINE,
                amount=fine,
                reason="Grooming check failed on selfie",
                punch_event_id=punch.id,
            )
        )
        await notify_user(
            db,
            user_id=user.id,
            title="Grooming fine",
            body=f"₹{fine:.0f} deducted from salary — selfie grooming check failed.",
            category="grooming_fine",
            link="/app/salary",
        )
        return f"Grooming fine ₹{fine:.0f} from salary"

    if student:
        # Track as meta; students pay fine separately — notify student + parents
        punch.meta_json = {**(punch.meta_json or {}), "student_fine": fine}
        await notify_user(
            db,
            user_id=user.id,
            title="Grooming fine",
            body=f"₹{fine:.0f} fine for failed grooming check. Please follow dress code.",
            category="grooming_fine",
            link="/app/punch",
        )
        from app.models import Parent

        parent_rows = (
            await db.execute(
                select(ParentStudent)
                .options(selectinload(ParentStudent.parent).selectinload(Parent.user))
                .where(ParentStudent.student_id == student.id)
            )
        ).scalars().all()
        for link in parent_rows:
            if link.parent and link.parent.user_id:
                await notify_user(
                    db,
                    user_id=link.parent.user_id,
                    title="Grooming fine for your child",
                    body=f"{user.full_name} received a ₹{fine:.0f} fine for grooming standards.",
                    category="grooming_fine",
                    link="/app/notifications",
                )
        return f"Student grooming fine ₹{fine:.0f}"
    return None


async def record_punch(
    db: AsyncSession,
    *,
    user: User,
    qr_token: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    accuracy_m: Optional[float] = None,
    selfie_bytes: Optional[bytes] = None,
) -> dict:
    settings = await get_punch_settings(db)
    role = user.role.name if user.role else None
    is_staff = role not in {UserRole.STUDENT, UserRole.PARENT, None}
    is_student = role == UserRole.STUDENT
    if role == UserRole.PARENT:
        raise ForbiddenError("Parents cannot punch attendance")

    staff = await db.scalar(
        select(Staff)
        .options(selectinload(Staff.branch))
        .where(Staff.user_id == user.id, Staff.is_active.is_(True))
    )
    student = await db.scalar(
        select(Student)
        .options(selectinload(Student.branch))
        .where(Student.user_id == user.id, Student.is_active.is_(True))
    )

    assigned_branch: Optional[Branch] = None
    if staff and staff.branch_id:
        assigned_branch = staff.branch or await db.scalar(select(Branch).where(Branch.id == staff.branch_id))
    elif student and student.branch_id:
        assigned_branch = student.branch or await db.scalar(
            select(Branch).where(Branch.id == student.branch_id)
        )

    if not assigned_branch or not assigned_branch.is_active:
        raise ValidationAppError(
            "No branch assigned. Ask Admin to set your punch branch/location first."
        )

    token = qr_token.strip()
    if token.startswith("caa-punch:"):
        token = token.split(":", 1)[1]

    # Prefer branch QR match; allow legacy global QR only if it matches assigned branch token
    qr_branch = await db.scalar(
        select(Branch).where(Branch.punch_token == token, Branch.is_active.is_(True))
    )
    if not qr_branch:
        # legacy global academy QR (old flow)
        active = await get_or_create_active_qr(db)
        if token != active.token:
            raise UnauthorizedError("Invalid punch QR. Use the QR for your assigned branch.")
        qr_branch = assigned_branch
    elif qr_branch.id != assigned_branch.id:
        raise UnauthorizedError(
            f"Wrong branch QR. You are assigned to {assigned_branch.name}. "
            f"Scan the QR at your branch only."
        )

    now = datetime.now(timezone.utc)
    local = _ist_now()
    today = local.date()
    month_key = today.strftime("%Y-%m")

    last_today = await db.scalar(
        select(PunchEvent)
        .where(PunchEvent.user_id == user.id, PunchEvent.punch_date == today)
        .order_by(PunchEvent.punched_at.desc())
        .limit(1)
    )
    punch_type = PunchType.OUT if last_today and last_today.punch_type == PunchType.IN else PunchType.IN

    start_str = (assigned_branch.staff_start if is_staff else assigned_branch.student_start) or (
        settings["staff_start"] if is_staff else settings["student_start"]
    )
    start_t = _parse_hhmm(start_str)
    grace = int(settings["late_grace_minutes"])
    is_late = False
    late_minutes = 0
    if punch_type == PunchType.IN:
        start_dt = datetime.combine(today, start_t, tzinfo=local.tzinfo)
        grace_deadline = start_dt + __import__("datetime").timedelta(minutes=grace)
        if local > grace_deadline:
            is_late = True
            late_minutes = int((local - start_dt).total_seconds() // 60)

    on_campus = None
    distance_m = None
    if latitude is not None and longitude is not None:
        distance_m = haversine_m(
            latitude, longitude, float(assigned_branch.latitude), float(assigned_branch.longitude)
        )
        on_campus = distance_m <= float(assigned_branch.geofence_radius_m)
    elif is_staff and settings.get("require_gps_for_staff"):
        raise ValidationAppError("GPS location is required for staff punch")

    selfie_url = None
    grooming_ok = None
    grooming_notes = None
    grooming_details: dict = {}
    if settings.get("require_selfie", True):
        if not selfie_bytes:
            raise ValidationAppError("Selfie is required for punch")
        grooming_ok, grooming_notes, grooming_details = await analyze_grooming(selfie_bytes)
        selfie_url = save_selfie(user.id, selfie_bytes)

    punch = PunchEvent(
        user_id=user.id,
        punch_type=punch_type,
        punched_at=now,
        punch_date=today,
        is_late=is_late,
        late_minutes=late_minutes,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        on_campus=on_campus,
        distance_m=distance_m,
        selfie_url=selfie_url,
        grooming_ok=grooming_ok,
        grooming_notes=grooming_notes,
        qr_token=qr_branch.punch_token if qr_branch else token,
        branch_id=assigned_branch.id,
        meta_json={
            "branch_code": assigned_branch.code,
            "branch_name": assigned_branch.name,
            "grooming": {
                "issues": grooming_details.get("issues") or [],
                "provider": grooming_details.get("provider"),
                "ai_ready": grooming_details.get("ai_ready"),
            },
        },
    )
    db.add(punch)
    await db.flush()

    effects: list[str] = []
    if punch_type == PunchType.IN and is_late:
        if staff:
            effects.extend(
                await _apply_staff_late_penalties(
                    db, staff=staff, user=user, punch=punch, settings=settings
                )
            )
        if student:
            effects.extend(await _apply_student_late(db, student=student, user=user, punch=punch))

    if grooming_ok is False:
        issues = [str(i) for i in (grooming_details.get("issues") or [])]
        # ₹500 only for real grooming fails — not for dark/blurry photo rejects
        chargeable = (not issues) or any(
            i in {"hair", "facial_grooming", "appearance"} for i in issues
        )
        if chargeable:
            note = await _apply_grooming_fine(
                db, user=user, staff=staff, student=student, punch=punch, settings=settings
            )
            if note:
                effects.append(note)
        else:
            effects.append("Selfie rejected for photo quality — retake (no fine)")

    if student and punch_type == PunchType.IN:
        note = await _sync_student_attendance_from_punch(db, student=student, punch=punch)
        if note:
            effects.append(note)

        from app.models import Parent

        parent_rows = (
            await db.execute(
                select(ParentStudent)
                .options(selectinload(ParentStudent.parent).selectinload(Parent.user))
                .where(ParentStudent.student_id == student.id)
            )
        ).scalars().all()
        status = "late" if is_late else "on time"
        for link in parent_rows:
            if link.parent and link.parent.user_id:
                await notify_user(
                    db,
                    user_id=link.parent.user_id,
                    title="Child punched in",
                    body=(
                        f"{user.full_name} punched IN at {assigned_branch.name} "
                        f"at {local.strftime('%I:%M %p')} ({status})."
                    ),
                    category="punch_in",
                    link="/app/parent/attendance",
                )

    if staff:
        await compute_salary_slip(db, staff_id=staff.id, month_key=month_key)

    return {
        "id": str(punch.id),
        "punch_type": punch.punch_type.value,
        "punched_at": punch.punched_at.isoformat(),
        "punch_date": punch.punch_date.isoformat(),
        "is_late": punch.is_late,
        "late_minutes": punch.late_minutes,
        "on_campus": punch.on_campus,
        "distance_m": round(distance_m, 1) if distance_m is not None else None,
        "branch": {"id": str(assigned_branch.id), "code": assigned_branch.code, "name": assigned_branch.name},
        "selfie_url": punch.selfie_url,
        "grooming_ok": punch.grooming_ok,
        "grooming_notes": punch.grooming_notes,
        "grooming_issues": grooming_details.get("issues") or [],
        "grooming_ai_ready": bool(grooming_details.get("ai_ready")),
        "effects": effects,
    }


async def compute_salary_slip(db: AsyncSession, *, staff_id: UUID, month_key: str) -> dict:
    staff = await db.scalar(
        select(Staff).options(selectinload(Staff.user)).where(Staff.id == staff_id)
    )
    if not staff:
        raise NotFoundError("Staff not found")

    base = float(staff.monthly_salary or 0)
    deductions = (
        await db.execute(
            select(PayrollDeduction).where(
                PayrollDeduction.staff_id == staff_id, PayrollDeduction.month_key == month_key
            )
        )
    ).scalars().all()
    total_ded = round(sum(d.amount for d in deductions), 2)
    net = round(max(0.0, base - total_ded), 2)

    late_days = int(
        await db.scalar(
            select(func.count()).select_from(LateWarning).where(
                LateWarning.user_id == staff.user_id, LateWarning.month_key == month_key
            )
        )
        or 0
    )
    year, month = map(int, month_key.split("-"))
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    month_start = date(year, month, 1)
    present_days = int(
        await db.scalar(
            select(func.count(func.distinct(PunchEvent.punch_date))).where(
                PunchEvent.user_id == staff.user_id,
                PunchEvent.punch_type == PunchType.IN,
                PunchEvent.punch_date >= month_start,
                PunchEvent.punch_date < next_month,
            )
        )
        or 0
    )

    details = {
        "deductions": [
            {
                "type": d.deduction_type.value,
                "amount": d.amount,
                "reason": d.reason,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in deductions
        ]
    }

    slip = await db.scalar(
        select(MonthlySalarySlip).where(
            MonthlySalarySlip.staff_id == staff_id, MonthlySalarySlip.month_key == month_key
        )
    )
    if not slip:
        slip = MonthlySalarySlip(
            staff_id=staff_id,
            month_key=month_key,
            base_salary=base,
            total_deductions=total_ded,
            net_salary=net,
            late_days=late_days,
            warnings=late_days,
            present_days=present_days,
            details_json=details,
        )
        db.add(slip)
    else:
        slip.base_salary = base
        slip.total_deductions = total_ded
        slip.net_salary = net
        slip.late_days = late_days
        slip.warnings = late_days
        slip.present_days = present_days
        slip.details_json = details
    await db.flush()

    return {
        "staff_id": str(staff.id),
        "employee_code": staff.employee_code,
        "name": staff.user.full_name if staff.user else "",
        "email": staff.user.email if staff.user else "",
        "month_key": month_key,
        "base_salary": base,
        "total_deductions": total_ded,
        "net_salary": net,
        "late_days": late_days,
        "warnings": late_days,
        "present_days": present_days,
        "deductions": details["deductions"],
        "on_campus_last": None,
    }


async def monthly_salary_report(db: AsyncSession, *, month_key: str) -> dict:
    staff_rows = (
        await db.execute(
            select(Staff)
            .options(selectinload(Staff.user))
            .where(Staff.is_active.is_(True))
        )
    ).scalars().all()
    items = []
    for staff in staff_rows:
        items.append(await compute_salary_slip(db, staff_id=staff.id, month_key=month_key))
    return {"month_key": month_key, "items": items, "total": len(items)}


async def staff_presence(db: AsyncSession) -> list[dict]:
    """Latest punch GPS snapshot for active staff."""
    staff_rows = (
        await db.execute(
            select(Staff)
            .options(selectinload(Staff.user), selectinload(Staff.branch))
            .where(Staff.is_active.is_(True))
        )
    ).scalars().all()
    out = []
    today = _ist_today()
    for staff in staff_rows:
        last = await db.scalar(
            select(PunchEvent)
            .where(PunchEvent.user_id == staff.user_id)
            .order_by(PunchEvent.punched_at.desc())
            .limit(1)
        )
        in_today = await db.scalar(
            select(PunchEvent).where(
                PunchEvent.user_id == staff.user_id,
                PunchEvent.punch_date == today,
                PunchEvent.punch_type == PunchType.IN,
            ).order_by(PunchEvent.punched_at.desc()).limit(1)
        )
        out_after = None
        if in_today:
            out_after = await db.scalar(
                select(PunchEvent).where(
                    PunchEvent.user_id == staff.user_id,
                    PunchEvent.punch_date == today,
                    PunchEvent.punch_type == PunchType.OUT,
                    PunchEvent.punched_at > in_today.punched_at,
                ).limit(1)
            )
        status = "absent"
        if in_today and not out_after:
            status = "on_campus" if in_today.on_campus else "punched_in_off_campus"
        elif in_today and out_after:
            status = "left"

        out.append(
            {
                "staff_id": str(staff.id),
                "name": staff.user.full_name if staff.user else "",
                "employee_code": staff.employee_code,
                "branch_id": str(staff.branch_id) if staff.branch_id else None,
                "branch_name": staff.branch.name if staff.branch else None,
                "status": status,
                "last_punch_type": last.punch_type.value if last else None,
                "last_punched_at": last.punched_at.isoformat() if last else None,
                "latitude": last.latitude if last else None,
                "longitude": last.longitude if last else None,
                "on_campus": last.on_campus if last else None,
                "distance_m": last.distance_m if last else None,
                "selfie_url": last.selfie_url if last else None,
            }
        )
    return out


async def my_punches(db: AsyncSession, *, user_id: UUID, limit: int = 30) -> list[dict]:
    rows = (
        await db.execute(
            select(PunchEvent)
            .where(PunchEvent.user_id == user_id)
            .order_by(PunchEvent.punched_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "punch_type": r.punch_type.value,
            "punched_at": r.punched_at.isoformat(),
            "punch_date": r.punch_date.isoformat(),
            "is_late": r.is_late,
            "late_minutes": r.late_minutes,
            "on_campus": r.on_campus,
            "grooming_ok": r.grooming_ok,
            "selfie_url": r.selfie_url,
        }
        for r in rows
    ]
