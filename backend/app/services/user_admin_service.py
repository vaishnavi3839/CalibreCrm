"""Admin provisioning of student and parent portal logins."""

from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.security import hash_password
from app.models import Parent, ParentStudent, Role, Student, User, UserRole
from app.services.staff_service import avatar_url


def _require_admin(actor: User) -> None:
    if actor.role.name not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise ForbiddenError("Only Admin can add or delete students and parents")


async def create_student(
    db: AsyncSession,
    *,
    created_by: User,
    full_name: str,
    email: str,
    phone: Optional[str] = None,
    student_code: Optional[str] = None,
    course_id: Optional[UUID] = None,
    batch_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    password: Optional[str] = None,
) -> dict:
    _require_admin(created_by)
    email = email.lower().strip()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise ConflictError("A user with this email already exists")

    if student_code:
        code = student_code.strip().upper()
        if await db.scalar(select(Student).where(Student.student_code == code)):
            raise ConflictError("Student code already in use")
    else:
        year = date.today().year
        count = await db.scalar(select(func.count()).select_from(Student)) or 0
        code = f"CAA-STU-{year}-{count + 1:03d}"

    role = await db.scalar(select(Role).where(Role.name == UserRole.STUDENT))
    if not role:
        raise NotFoundError("Student role missing — run seed first")

    temp_password = password or "Password123!"
    user = User(
        email=email,
        full_name=full_name.strip(),
        phone=phone,
        password_hash=hash_password(temp_password),
        role_id=role.id,
        must_change_password=True,
        photo_url=avatar_url(full_name),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    student = Student(
        user_id=user.id,
        student_code=code,
        course_id=course_id,
        batch_id=batch_id,
        branch_id=branch_id,
        enrollment_date=date.today(),
        academic_status="active",
    )
    db.add(student)
    await db.flush()

    return {
        "id": str(student.id),
        "user_id": str(user.id),
        "student_code": student.student_code,
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "temporary_password": temp_password,
        "must_change_password": True,
    }


async def deactivate_student(db: AsyncSession, *, student_id: UUID, deleted_by: User) -> dict:
    _require_admin(deleted_by)
    student = await db.scalar(
        select(Student).options(selectinload(Student.user)).where(Student.id == student_id)
    )
    if not student or not student.is_active:
        raise NotFoundError("Student not found")
    student.is_active = False
    student.academic_status = "inactive"
    if student.user:
        student.user.is_active = False
    await db.flush()
    return {"id": str(student.id), "deactivated": True}


async def update_student(
    db: AsyncSession,
    *,
    student_id: UUID,
    updated_by: User,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    student_code: Optional[str] = None,
    course_id: Optional[UUID] = None,
    batch_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    password: Optional[str] = None,
    clear_course: bool = False,
    clear_batch: bool = False,
    clear_branch: bool = False,
) -> dict:
    _require_admin(updated_by)
    student = await db.scalar(
        select(Student).options(selectinload(Student.user)).where(Student.id == student_id, Student.is_active.is_(True))
    )
    if not student or not student.user:
        raise NotFoundError("Student not found")

    user = student.user
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

    if student_code is not None and student_code.strip():
        code = student_code.strip().upper()
        other = await db.scalar(select(Student).where(Student.student_code == code, Student.id != student.id))
        if other:
            raise ConflictError("Student code already in use")
        student.student_code = code

    if clear_course:
        student.course_id = None
    elif course_id is not None:
        student.course_id = course_id
    if clear_batch:
        student.batch_id = None
    elif batch_id is not None:
        student.batch_id = batch_id
    if clear_branch:
        student.branch_id = None
    elif branch_id is not None:
        student.branch_id = branch_id

    await db.flush()
    return {
        "id": str(student.id),
        "student_code": student.student_code,
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "course_id": str(student.course_id) if student.course_id else None,
        "batch_id": str(student.batch_id) if student.batch_id else None,
        "branch_id": str(student.branch_id) if student.branch_id else None,
    }


async def create_parent(
    db: AsyncSession,
    *,
    created_by: User,
    full_name: str,
    email: str,
    phone: Optional[str] = None,
    relationship_type: str = "parent",
    student_id: Optional[UUID] = None,
    password: Optional[str] = None,
) -> dict:
    _require_admin(created_by)
    email = email.lower().strip()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise ConflictError("A user with this email already exists")

    role = await db.scalar(select(Role).where(Role.name == UserRole.PARENT))
    if not role:
        raise NotFoundError("Parent role missing — run seed first")

    temp_password = password or "Password123!"
    user = User(
        email=email,
        full_name=full_name.strip(),
        phone=phone,
        password_hash=hash_password(temp_password),
        role_id=role.id,
        must_change_password=True,
        photo_url=avatar_url(full_name),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    parent = Parent(user_id=user.id, relationship_type=relationship_type or "parent")
    db.add(parent)
    await db.flush()

    linked_student = None
    if student_id:
        student = await db.get(Student, student_id)
        if not student or not student.is_active:
            raise NotFoundError("Student not found to link")
        db.add(ParentStudent(parent_id=parent.id, student_id=student.id, is_primary=True))
        linked_student = str(student.id)
        await db.flush()

    return {
        "id": str(parent.id),
        "user_id": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "relationship_type": parent.relationship_type,
        "linked_student_id": linked_student,
        "temporary_password": temp_password,
        "must_change_password": True,
    }


async def deactivate_parent(db: AsyncSession, *, parent_id: UUID, deleted_by: User) -> dict:
    _require_admin(deleted_by)
    parent = await db.scalar(
        select(Parent).options(selectinload(Parent.user)).where(Parent.id == parent_id)
    )
    if not parent or not parent.is_active:
        raise NotFoundError("Parent not found")
    parent.is_active = False
    if parent.user:
        parent.user.is_active = False
    await db.flush()
    return {"id": str(parent.id), "deactivated": True}


async def list_parents(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Parent)
            .options(
                selectinload(Parent.user),
                selectinload(Parent.students).selectinload(ParentStudent.student).selectinload(Student.user),
            )
            .where(Parent.is_active.is_(True))
            .order_by(Parent.created_at.desc())
        )
    ).scalars().all()
    items = []
    for p in rows:
        children = []
        for link in p.students or []:
            s = link.student
            if s and s.user:
                children.append({"id": str(s.id), "name": s.user.full_name, "student_code": s.student_code})
        items.append(
            {
                "id": str(p.id),
                "user_id": str(p.user_id),
                "name": p.user.full_name if p.user else None,
                "email": p.user.email if p.user else None,
                "phone": p.user.phone if p.user else None,
                "relationship_type": p.relationship_type,
                "students": children,
            }
        )
    return items
