from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.core.response import success
from app.models import Branch, Staff, UserRole
from app.services import staff_service

router = APIRouter(prefix="/staff", tags=["staff"])


class StaffCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    employee_code: str = Field(min_length=3, max_length=50)
    department: Optional[str] = None
    designation: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    available_for_leads: bool = False
    finance_access: bool = False
    monthly_salary: Optional[float] = Field(default=0, ge=0)
    branch_id: Optional[str] = None


@router.get("")
async def list_staff(
    user: CurrentUser,
    db: DbSession,
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
):
    if user.role.name not in {
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.RM,
    }:
        raise ForbiddenError()
    items = await staff_service.list_staff(db, role=role, search=search)
    return success({"items": items, "total": len(items)})


@router.post("")
async def create_staff(payload: StaffCreateRequest, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    created = await staff_service.create_staff(
        db,
        created_by=user,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role_name=payload.role,
        employee_code=payload.employee_code,
        department=payload.department,
        designation=payload.designation,
        password=payload.password,
        available_for_leads=payload.available_for_leads,
        finance_access=payload.finance_access,
        monthly_salary=payload.monthly_salary or 0,
        branch_id=payload.branch_id,
    )
    return JSONResponse(
        status_code=201,
        content=success(created, message="Staff member created successfully", status_code=201),
    )


class StaffUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    employee_code: Optional[str] = Field(default=None, min_length=3, max_length=50)
    department: Optional[str] = None
    designation: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    available_for_leads: Optional[bool] = None
    finance_access: Optional[bool] = None
    monthly_salary: Optional[float] = Field(default=None, ge=0)
    branch_id: Optional[str] = None


@router.put("/{staff_id}")
async def update_staff(staff_id: UUID, payload: StaffUpdateRequest, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError()
    updated = await staff_service.update_staff(
        db,
        staff_id=staff_id,
        updated_by=user,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role_name=payload.role,
        employee_code=payload.employee_code,
        department=payload.department,
        designation=payload.designation,
        password=payload.password,
        available_for_leads=payload.available_for_leads,
        finance_access=payload.finance_access,
        monthly_salary=payload.monthly_salary,
        branch_id=payload.branch_id,
    )
    return success(updated, message="Staff updated")


class StaffBranchAssign(BaseModel):
    branch_id: UUID


@router.put("/{staff_id}/branch")
async def assign_staff_branch(staff_id: UUID, payload: StaffBranchAssign, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError()
    staff = await db.scalar(select(Staff).where(Staff.id == staff_id, Staff.is_active.is_(True)))
    if not staff:
        raise NotFoundError("Staff not found")
    branch = await db.scalar(select(Branch).where(Branch.id == payload.branch_id, Branch.is_active.is_(True)))
    if not branch:
        raise ValidationAppError("Branch not found")
    staff.branch_id = branch.id
    await db.flush()
    return success(
        {"staff_id": str(staff.id), "branch_id": str(branch.id), "branch_name": branch.name},
        message="Staff punch branch updated",
    )


@router.delete("/{staff_id}")
async def delete_staff(staff_id: str, user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    result = await staff_service.deactivate_staff(db, staff_id=UUID(staff_id), deleted_by=user)
    return success(result, message="Staff deleted")


@router.get("/daily-report")
async def daily_report(
    user: CurrentUser,
    db: DbSession,
    report_date: Optional[date] = Query(default=None, alias="date"),
):
    if user.role.name not in {
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.RM,
    }:
        raise ForbiddenError()
    report = await staff_service.daily_staff_report(db, on_date=report_date)
    return success(report)


@router.get("/top-performer")
async def top_performer(user: CurrentUser, db: DbSession):
    """Visible to all authenticated staff (not students/parents)."""
    if user.role.name in {UserRole.STUDENT, UserRole.PARENT}:
        raise ForbiddenError()
    data = await staff_service.get_top_performer(db)
    return success(data)
