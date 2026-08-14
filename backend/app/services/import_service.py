"""Bulk lead import from CSV / Excel with validation and duplicate detection."""

from __future__ import annotations

import io
import re
from typing import Any, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, LeadSource, User
from app.services import lead_service

REQUIRED_COLUMNS = ["name", "phone"]
OPTIONAL_COLUMNS = ["email", "location", "age", "course", "source", "notes"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

SOURCE_ALIASES = {
    "website": LeadSource.WEBSITE,
    "web": LeadSource.WEBSITE,
    "instagram": LeadSource.INSTAGRAM,
    "ig": LeadSource.INSTAGRAM,
    "insta": LeadSource.INSTAGRAM,
    "facebook": LeadSource.FACEBOOK,
    "fb": LeadSource.FACEBOOK,
    "google ads": LeadSource.GOOGLE_ADS,
    "google_ads": LeadSource.GOOGLE_ADS,
    "google": LeadSource.GOOGLE_ADS,
    "whatsapp": LeadSource.WHATSAPP,
    "wa": LeadSource.WHATSAPP,
    "walk-in": LeadSource.WALK_IN,
    "walk_in": LeadSource.WALK_IN,
    "walkin": LeadSource.WALK_IN,
    "referral": LeadSource.REFERRAL,
    "youtube": LeadSource.YOUTUBE,
    "yt": LeadSource.YOUTUBE,
    "event": LeadSource.EVENT,
    "college visit": LeadSource.COLLEGE_VISIT,
    "college_visit": LeadSource.COLLEGE_VISIT,
    "existing student": LeadSource.EXISTING_STUDENT,
    "existing_student": LeadSource.EXISTING_STUDENT,
    "other": LeadSource.OTHER,
}


def _normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "full_name": "name",
        "student_name": "name",
        "mobile": "phone",
        "mobile_number": "phone",
        "phone_number": "phone",
        "contact": "phone",
        "e_mail": "email",
        "mail": "email",
        "city": "location",
        "lead_source": "source",
        "course_interested": "course",
        "course_name": "course",
        "remark": "notes",
        "remarks": "notes",
        "comment": "notes",
    }
    return aliases.get(text, text)


def _clean_phone(value: Any) -> str:
    raw = str(value or "").strip()
    if raw.endswith(".0"):
        raw = raw[:-2]
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("+91") and len(digits) == 13:
        digits = digits[3:]
    return digits


def _parse_source(value: Any) -> Optional[LeadSource]:
    if value is None or str(value).strip() == "" or str(value).lower() == "nan":
        return LeadSource.OTHER
    key = str(value).strip().lower().replace("-", " ")
    key2 = key.replace(" ", "_")
    return SOURCE_ALIASES.get(key) or SOURCE_ALIASES.get(key2) or LeadSource.OTHER


def parse_import_file(content: bytes, filename: str) -> pd.DataFrame:
    name = (filename or "").lower()
    buffer = io.BytesIO(content)
    if name.endswith(".csv"):
        df = pd.read_csv(buffer)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(buffer)
    else:
        raise ValueError("Unsupported file type. Upload .xlsx, .xls, or .csv")

    if df.empty:
        raise ValueError("File has no rows")

    df.columns = [_normalize_header(c) for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}. Expected at least: name, phone")

    # Keep known columns only
    keep = [c for c in ALL_COLUMNS if c in df.columns]
    return df[keep].fillna("")


async def preview_import(db: AsyncSession, content: bytes, filename: str) -> dict:
    df = parse_import_file(content, filename)
    courses = (await db.execute(select(Course).where(Course.is_active.is_(True)))).scalars().all()
    course_by_code = {c.code.lower(): c for c in courses}
    course_by_name = {c.name.lower(): c for c in courses}

    rows: list[dict] = []
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    seen_phones: set[str] = set()

    for idx, record in df.iterrows():
        row_number = int(idx) + 2  # header is row 1
        name = str(record.get("name", "")).strip()
        phone = _clean_phone(record.get("phone", ""))
        email_raw = str(record.get("email", "")).strip()
        email = email_raw if email_raw and email_raw.lower() != "nan" else None
        location = str(record.get("location", "")).strip() or None
        notes = str(record.get("notes", "")).strip() or None
        course_raw = str(record.get("course", "")).strip()
        source = _parse_source(record.get("source", ""))

        errors: list[str] = []
        warnings: list[str] = []

        if len(name) < 2:
            errors.append("Name is required")
        if len(phone) < 8 or len(phone) > 15 or not re.fullmatch(r"\d{8,15}", phone):
            errors.append("Invalid phone number")

        age = None
        age_raw = str(record.get("age", "")).strip()
        if age_raw and age_raw.lower() != "nan":
            try:
                age = int(float(age_raw))
                if age < 10 or age > 80:
                    errors.append("Age must be between 10 and 80")
            except ValueError:
                errors.append("Age must be a number")

        course_id = None
        if course_raw and course_raw.lower() != "nan":
            course = course_by_code.get(course_raw.lower()) or course_by_name.get(course_raw.lower())
            if not course:
                # partial name match
                for c in courses:
                    if course_raw.lower() in c.name.lower() or course_raw.lower() == c.code.lower():
                        course = c
                        break
            if course:
                course_id = str(course.id)
            else:
                warnings.append(f"Course '{course_raw}' not found — lead will import without course")

        duplicates = []
        if phone and not errors:
            if phone in seen_phones:
                warnings.append("Duplicate phone within this file")
                duplicate_count += 1
            else:
                seen_phones.add(phone)
            existing = await lead_service.find_duplicate_leads(db, phone, email)
            if existing:
                duplicate_count += 1
                warnings.append("Possible duplicate lead found in CRM")
                duplicates = [
                    {"id": str(d.id), "lead_code": d.lead_code, "name": d.name, "phone": d.phone}
                    for d in existing
                ]

        status = "invalid" if errors else ("duplicate" if duplicates or "Duplicate phone within this file" in warnings else "valid")
        if status == "valid":
            valid_count += 1
        elif status == "invalid":
            invalid_count += 1
        else:
            valid_count += 1  # duplicates can still be imported if user confirms

        rows.append(
            {
                "row_number": row_number,
                "status": status,
                "name": name,
                "phone": phone,
                "email": email,
                "location": location,
                "age": age,
                "course": course_raw or None,
                "course_id": course_id,
                "source": source.value if source else "other",
                "notes": notes,
                "errors": errors,
                "warnings": warnings,
                "duplicates": duplicates,
            }
        )

    return {
        "filename": filename,
        "total_rows": len(rows),
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "duplicate_rows": duplicate_count,
        "columns_detected": list(df.columns),
        "rows": rows,
    }


async def commit_import(
    db: AsyncSession,
    *,
    rows: list[dict],
    created_by: User,
    auto_assign: bool = True,
    skip_invalid: bool = True,
    skip_duplicates: bool = False,
) -> dict:
    created = 0
    skipped = 0
    failed = 0
    assigned = 0
    results = []

    for row in rows:
        if row.get("errors"):
            if skip_invalid:
                skipped += 1
                results.append({"row_number": row.get("row_number"), "status": "skipped_invalid"})
                continue
            failed += 1
            results.append({"row_number": row.get("row_number"), "status": "failed_invalid"})
            continue

        if skip_duplicates and (row.get("duplicates") or "Duplicate phone within this file" in (row.get("warnings") or [])):
            skipped += 1
            results.append({"row_number": row.get("row_number"), "status": "skipped_duplicate"})
            continue

        try:
            from uuid import UUID

            course_id = UUID(row["course_id"]) if row.get("course_id") else None
            source = LeadSource(row.get("source") or "other")
            lead, duplicates = await lead_service.create_lead(
                db,
                name=row["name"],
                phone=row["phone"],
                email=row.get("email"),
                location=row.get("location"),
                age=row.get("age"),
                course_id=course_id,
                source=source,
                notes=row.get("notes"),
                created_by=created_by,
                auto_assign=auto_assign,
            )
            created += 1
            if lead.assigned_staff_id:
                assigned += 1
            results.append(
                {
                    "row_number": row.get("row_number"),
                    "status": "created",
                    "lead_id": str(lead.id),
                    "lead_code": lead.lead_code,
                    "duplicate_warning": bool(duplicates),
                }
            )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            results.append({"row_number": row.get("row_number"), "status": "failed", "error": str(exc)})

    return {
        "created": created,
        "assigned": assigned,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }


def build_template_bytes() -> bytes:
    df = pd.DataFrame(
        [
            {
                "name": "Rahul Kumar",
                "phone": "9876543210",
                "email": "rahul@example.com",
                "location": "Bengaluru",
                "age": 19,
                "course": "CPL",
                "source": "instagram",
                "notes": "Interested in commercial pilot training",
            },
            {
                "name": "Sneha Reddy",
                "phone": "9876543211",
                "email": "sneha@example.com",
                "location": "Hyderabad",
                "age": 21,
                "course": "Cabin Crew",
                "source": "website",
                "notes": "Asked about hostel",
            },
        ]
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Leads")
    return buffer.getvalue()
