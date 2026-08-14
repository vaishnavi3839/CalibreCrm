"""QR punch, academy settings, GPS presence, and salary reports."""

from __future__ import annotations

import base64
import csv
import io
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ForbiddenError
from app.core.response import success
from app.models import Staff, UserRole
from app.services import punch_service
from sqlalchemy import select

router = APIRouter(prefix="/punch", tags=["punch"])


class PunchSettingsUpdate(BaseModel):
    staff_start: Optional[str] = None
    staff_end: Optional[str] = None
    student_start: Optional[str] = None
    student_end: Optional[str] = None
    late_grace_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    staff_late_warnings_for_half_day: Optional[int] = Field(default=None, ge=1, le=31)
    staff_warnings_for_half_salary: Optional[int] = Field(default=None, ge=1, le=31)
    grooming_fine: Optional[float] = Field(default=None, ge=0)
    working_days_per_month: Optional[int] = Field(default=None, ge=1, le=31)
    academy_lat: Optional[float] = None
    academy_lng: Optional[float] = None
    geofence_radius_m: Optional[float] = Field(default=None, ge=20, le=5000)
    require_selfie: Optional[bool] = None
    require_gps_for_staff: Optional[bool] = None


def _qr_png_data_url(token: str) -> str:
    import qrcode

    payload = f"caa-punch:{token}"
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


@router.get("/settings")
async def get_settings(user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError()
    return success(await punch_service.get_punch_settings(db))


@router.put("/settings")
async def update_settings(payload: PunchSettingsUpdate, user: CurrentUser, db: DbSession):
    data = await punch_service.save_punch_settings(
        db, updates=payload.model_dump(exclude_none=True), actor=user
    )
    return success(data, message="Punch settings saved")


@router.get("/qr")
async def get_punch_qr(user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError()
    qr = await punch_service.get_or_create_active_qr(db)
    return success(
        {
            "token": qr.token,
            "payload": f"caa-punch:{qr.token}",
            "qr_image": _qr_png_data_url(qr.token),
            "label": qr.label,
        }
    )


@router.post("/qr/rotate")
async def rotate_qr(user: CurrentUser, db: DbSession):
    qr = await punch_service.rotate_punch_qr(db, actor=user)
    return success(
        {
            "token": qr.token,
            "payload": f"caa-punch:{qr.token}",
            "qr_image": _qr_png_data_url(qr.token),
            "label": qr.label,
        },
        message="Punch QR rotated",
    )


@router.post("")
async def punch_in_out(
    user: CurrentUser,
    db: DbSession,
    qr_token: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    accuracy_m: Optional[float] = Form(None),
    selfie: Optional[UploadFile] = File(None),
):
    selfie_bytes = await selfie.read() if selfie else None
    result = await punch_service.record_punch(
        db,
        user=user,
        qr_token=qr_token,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        selfie_bytes=selfie_bytes,
    )
    return success(result, message=f"Punched {result['punch_type'].upper()}")


@router.get("/me")
async def my_punch_history(user: CurrentUser, db: DbSession):
    return success({"items": await punch_service.my_punches(db, user_id=user.id)})


@router.get("/presence")
async def staff_presence(user: CurrentUser, db: DbSession):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.RM}:
        raise ForbiddenError()
    return success({"items": await punch_service.staff_presence(db)})


@router.get("/salary")
async def salary_report(
    user: CurrentUser,
    db: DbSession,
    month: Optional[str] = Query(None, description="YYYY-MM"),
):
    month_key = month or date.today().strftime("%Y-%m")
    if user.role.name in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ACCOUNTANT}:
        return success(await punch_service.monthly_salary_report(db, month_key=month_key))

    staff = await db.scalar(select(Staff).where(Staff.user_id == user.id, Staff.is_active.is_(True)))
    if not staff:
        raise ForbiddenError("No staff salary profile")
    slip = await punch_service.compute_salary_slip(db, staff_id=staff.id, month_key=month_key)
    return success({"month_key": month_key, "items": [slip], "total": 1})


@router.get("/salary/download")
async def salary_report_csv(
    user: CurrentUser,
    db: DbSession,
    month: Optional[str] = Query(None),
):
    if user.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ACCOUNTANT}:
        raise ForbiddenError()
    month_key = month or date.today().strftime("%Y-%m")
    report = await punch_service.monthly_salary_report(db, month_key=month_key)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Employee Code",
            "Name",
            "Email",
            "Base Salary",
            "Present Days",
            "Late Days",
            "Warnings",
            "Total Deductions",
            "Net Salary",
            "Deduction Details",
        ]
    )
    for item in report["items"]:
        details = "; ".join(
            f"{d['type']}:₹{d['amount']} ({d['reason']})" for d in item.get("deductions") or []
        )
        writer.writerow(
            [
                item["employee_code"],
                item["name"],
                item["email"],
                item["base_salary"],
                item["present_days"],
                item["late_days"],
                item["warnings"],
                item["total_deductions"],
                item["net_salary"],
                details,
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="salary-{month_key}.csv"'},
    )
