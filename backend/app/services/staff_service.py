"""Staff management and daily productivity reports."""

from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.security import hash_password
from app.models import (
    Role,
    Staff,
    StaffPerformanceDaily,
    StaffTarget,
    User,
    UserRole,
)


STAFF_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.RM,
    UserRole.TELECALLER,
    UserRole.INSTRUCTOR,
    UserRole.ACCOUNTANT,
}


def avatar_url(name: str, photo_url: Optional[str] = None) -> str:
    if photo_url:
        return photo_url
    seed = name.replace(" ", "")
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={seed}&backgroundColor=0a1628"


async def get_top_performer(db: AsyncSession, on_date: Optional[date] = None) -> Optional[dict]:
    on_date = on_date or date.today()
    top = (
        await db.execute(
            select(StaffPerformanceDaily)
            .where(StaffPerformanceDaily.performance_date == on_date)
            .order_by(StaffPerformanceDaily.score.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not top:
        return None
    staff = await db.scalar(
        select(Staff).options(selectinload(Staff.user)).where(Staff.id == top.staff_id)
    )
    if not staff or not staff.user:
        return None
    return {
        "name": staff.user.full_name,
        "photo_url": avatar_url(staff.user.full_name, staff.user.photo_url),
        "score": top.score,
        "calls": top.calls_completed,
        "admissions": top.admissions,
        "employee_code": staff.employee_code,
        "staff_id": str(staff.id),
    }


async def daily_staff_report(db: AsyncSession, on_date: Optional[date] = None) -> dict:
    on_date = on_date or date.today()
    rows = (
        await db.execute(
            select(StaffPerformanceDaily)
            .where(StaffPerformanceDaily.performance_date == on_date)
            .order_by(StaffPerformanceDaily.score.desc())
        )
    ).scalars().all()

    items = []
    totals = {
        "leads_assigned": 0,
        "calls_completed": 0,
        "connected_calls": 0,
        "followups_completed": 0,
        "followups_missed": 0,
        "hot_leads": 0,
        "registrations": 0,
        "admissions": 0,
        "tasks_completed": 0,
    }

    for row in rows:
        staff = await db.scalar(
            select(Staff).options(selectinload(Staff.user).selectinload(User.role)).where(Staff.id == row.staff_id)
        )
        if not staff or not staff.user:
            continue
        # Targets for the day
        targets = (
            await db.execute(
                select(StaffTarget).where(
                    StaffTarget.staff_id == staff.id,
                    StaffTarget.period_type == "daily",
                    StaffTarget.period_start <= on_date,
                    StaffTarget.period_end >= on_date,
                )
            )
        ).scalars().all()
        target_map = {t.metric_key: {"target": t.target_value, "current": t.current_value} for t in targets}

        item = {
            "staff_id": str(staff.id),
            "employee_code": staff.employee_code,
            "name": staff.user.full_name,
            "role": staff.user.role.name.value if staff.user.role else None,
            "photo_url": avatar_url(staff.user.full_name, staff.user.photo_url),
            "leads_assigned": row.leads_assigned,
            "calls_completed": row.calls_completed,
            "connected_calls": row.connected_calls,
            "followups_completed": row.followups_completed,
            "followups_missed": row.followups_missed,
            "hot_leads": row.hot_leads,
            "warm_leads": row.warm_leads,
            "registrations": row.registrations,
            "admissions": row.admissions,
            "tasks_completed": row.tasks_completed,
            "score": row.score,
            "badges": row.badges or [],
            "targets": target_map,
        }
        items.append(item)
        for k in totals:
            totals[k] += getattr(row, k, 0) or 0

    return {
        "date": on_date.isoformat(),
        "staff_count": len(items),
        "totals": totals,
        "top_performer": items[0] if items else None,
        "items": items,
    }


async def list_staff(db: AsyncSession, *, role: Optional[UserRole] = None, search: Optional[str] = None) -> list[dict]:
    stmt = select(Staff).options(
        selectinload(Staff.user).selectinload(User.role),
        selectinload(Staff.branch),
    ).where(Staff.is_active.is_(True))
    rows = (await db.execute(stmt.order_by(Staff.employee_code.asc()))).scalars().all()
    items = []
    for s in rows:
        if not s.user:
            continue
        if role and s.user.role and s.user.role.name != role:
            continue
        if search:
            q = search.lower()
            hay = f"{s.user.full_name} {s.user.email} {s.employee_code}".lower()
            if q not in hay:
                continue
        items.append(
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "employee_code": s.employee_code,
                "name": s.user.full_name,
                "email": s.user.email,
                "phone": s.user.phone,
                "role": s.user.role.name.value if s.user.role else None,
                "role_display": s.user.role.display_name if s.user.role else None,
                "department": s.department,
                "designation": s.designation,
                "monthly_salary": float(s.monthly_salary or 0),
                "branch_id": str(s.branch_id) if s.branch_id else None,
                "branch_name": s.branch.name if s.branch else None,
                "branch_code": s.branch.code if s.branch else None,
                "is_available_for_leads": s.is_available_for_leads,
                "photo_url": avatar_url(s.user.full_name, s.user.photo_url),
                "is_active": s.user.is_active,
            }
        )
    return items


async def create_staff(
    db: AsyncSession,
    *,
    created_by: User,
    full_name: str,
    email: str,
    phone: Optional[str],
    role_name: UserRole,
    employee_code: str,
    department: Optional[str] = None,
    designation: Optional[str] = None,
    password: Optional[str] = None,
    available_for_leads: bool = False,
    finance_access: bool = False,
    monthly_salary: float = 0,
    branch_id: Optional[str] = None,
) -> dict:
    if created_by.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        # RM can create telecallers only
        if created_by.role.name != UserRole.RM or role_name != UserRole.TELECALLER:
            raise ForbiddenError("Only Admin/Super Admin can add this staff role")

    if role_name not in STAFF_ROLES:
        raise ValidationAppError("Invalid staff role")
    if role_name == UserRole.SUPER_ADMIN and created_by.role.name != UserRole.SUPER_ADMIN:
        raise ForbiddenError("Only Super Admin can create Super Admin")

    email = email.lower().strip()
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user:
        raise ConflictError("A user with this email already exists")

    existing_code = await db.scalar(select(Staff).where(Staff.employee_code == employee_code))
    if existing_code:
        raise ConflictError("Employee code already in use")

    role = await db.scalar(select(Role).where(Role.name == role_name))
    if not role:
        raise NotFoundError("Role not found — run seed/migrations first")

    temp_password = password or "Password123!"
    extra = {}
    if finance_access:
        extra["finance_access"] = True

    user = User(
        email=email,
        full_name=full_name.strip(),
        phone=phone,
        password_hash=hash_password(temp_password),
        role_id=role.id,
        extra_permissions=extra,
        must_change_password=True,
        photo_url=avatar_url(full_name),
    )
    db.add(user)
    await db.flush()

    from uuid import UUID as UUIDType

    branch_uuid = None
    if branch_id:
        try:
            branch_uuid = UUIDType(str(branch_id))
        except ValueError:
            raise ValidationAppError("Invalid branch_id")

    staff = Staff(
        user_id=user.id,
        employee_code=employee_code.strip().upper(),
        department=department,
        designation=designation,
        joining_date=date.today(),
        languages=["English", "Hindi"],
        is_available_for_leads=available_for_leads or role_name == UserRole.TELECALLER,
        monthly_salary=float(monthly_salary or 0),
        branch_id=branch_uuid,
    )
    db.add(staff)
    await db.flush()

    return {
        "id": str(staff.id),
        "user_id": str(user.id),
        "employee_code": staff.employee_code,
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": role_name.value,
        "monthly_salary": staff.monthly_salary,
        "temporary_password": temp_password,
        "must_change_password": True,
        "photo_url": user.photo_url,
    }


async def deactivate_staff(db: AsyncSession, *, staff_id, deleted_by: User) -> dict:
    if deleted_by.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError("Only Admin/RM can delete staff")

    staff = await db.scalar(
        select(Staff).options(selectinload(Staff.user).selectinload(User.role)).where(Staff.id == staff_id)
    )
    if not staff or not staff.is_active:
        raise NotFoundError("Staff not found")

    if staff.user_id == deleted_by.id:
        raise ValidationAppError("You cannot delete your own staff profile")

    if staff.user and staff.user.role and staff.user.role.name == UserRole.SUPER_ADMIN:
        if deleted_by.role.name != UserRole.SUPER_ADMIN:
            raise ForbiddenError("Only Super Admin can delete a Super Admin")

    staff.is_active = False
    staff.is_available_for_leads = False
    if staff.user:
        staff.user.is_active = False
    await db.flush()
    return {"id": str(staff.id), "deactivated": True}


async def update_staff(
    db: AsyncSession,
    *,
    staff_id: UUID,
    updated_by: User,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    role_name: Optional[UserRole] = None,
    employee_code: Optional[str] = None,
    department: Optional[str] = None,
    designation: Optional[str] = None,
    monthly_salary: Optional[float] = None,
    branch_id: Optional[str] = None,
    available_for_leads: Optional[bool] = None,
    finance_access: Optional[bool] = None,
    password: Optional[str] = None,
) -> dict:
    if updated_by.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError("Only Admin can edit staff")

    staff = await db.scalar(
        select(Staff)
        .options(selectinload(Staff.user).selectinload(User.role), selectinload(Staff.branch))
        .where(Staff.id == staff_id, Staff.is_active.is_(True))
    )
    if not staff or not staff.user:
        raise NotFoundError("Staff not found")

    user = staff.user
    if full_name is not None:
        user.full_name = full_name.strip()
    if phone is not None:
        user.phone = phone or None
    if email is not None:
        new_email = email.lower().strip()
        if new_email != user.email:
            exists = await db.scalar(select(User).where(User.email == new_email, User.id != user.id))
            if exists:
                raise ConflictError("A user with this email already exists")
            user.email = new_email
    if password:
        user.password_hash = hash_password(password)
        user.must_change_password = True

    if role_name is not None:
        if role_name not in STAFF_ROLES:
            raise ValidationAppError("Invalid staff role")
        if role_name == UserRole.SUPER_ADMIN and updated_by.role.name != UserRole.SUPER_ADMIN:
            raise ForbiddenError("Only Super Admin can assign Super Admin")
        role = await db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            raise NotFoundError("Role not found")
        user.role_id = role.id

    if finance_access is not None:
        extra = dict(user.extra_permissions or {})
        if finance_access:
            extra["finance_access"] = True
        else:
            extra.pop("finance_access", None)
        user.extra_permissions = extra

    if employee_code is not None:
        code = employee_code.strip().upper()
        other = await db.scalar(select(Staff).where(Staff.employee_code == code, Staff.id != staff.id))
        if other:
            raise ConflictError("Employee code already in use")
        staff.employee_code = code
    if department is not None:
        staff.department = department or None
    if designation is not None:
        staff.designation = designation or None
    if monthly_salary is not None:
        staff.monthly_salary = float(monthly_salary)
    if available_for_leads is not None:
        staff.is_available_for_leads = available_for_leads
    if branch_id is not None:
        if branch_id == "":
            staff.branch_id = None
        else:
            try:
                staff.branch_id = UUID(str(branch_id))
            except ValueError:
                raise ValidationAppError("Invalid branch_id")

    await db.flush()
    await db.refresh(staff)
    return {
        "id": str(staff.id),
        "employee_code": staff.employee_code,
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role.name.value if user.role else None,
        "department": staff.department,
        "designation": staff.designation,
        "monthly_salary": float(staff.monthly_salary or 0),
        "branch_id": str(staff.branch_id) if staff.branch_id else None,
    }
