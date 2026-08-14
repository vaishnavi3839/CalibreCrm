from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from sqlalchemy import (
    Uuid,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Index,
    JSON,
    Numeric,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SoftDeleteMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ─── Enums ───────────────────────────────────────────────────────────────────


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    RM = "rm"
    TELECALLER = "telecaller"
    INSTRUCTOR = "instructor"
    ACCOUNTANT = "accountant"
    STUDENT = "student"
    PARENT = "parent"


class LeadSource(str, Enum):
    WEBSITE = "website"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    GOOGLE_ADS = "google_ads"
    WHATSAPP = "whatsapp"
    WALK_IN = "walk_in"
    REFERRAL = "referral"
    YOUTUBE = "youtube"
    EVENT = "event"
    COLLEGE_VISIT = "college_visit"
    EXISTING_STUDENT = "existing_student"
    OTHER = "other"


class LeadStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    CONTACTED = "contacted"
    FOLLOW_UP = "follow_up"
    INTERESTED = "interested"
    COUNSELLING = "counselling"
    CAMPUS_VISIT = "campus_visit"
    REGISTRATION = "registration"
    CONVERTED = "converted"
    NOT_INTERESTED = "not_interested"
    LOST = "lost"
    INVALID_NUMBER = "invalid_number"


class LeadTemperature(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class CallOutcome(str, Enum):
    CONNECTED = "connected"
    NOT_ANSWERED = "not_answered"
    BUSY = "busy"
    SWITCHED_OFF = "switched_off"
    WRONG_NUMBER = "wrong_number"
    CALL_LATER = "call_later"


class FollowUpStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    MISSED = "missed"
    RESCHEDULED = "rescheduled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


class AnnouncementType(str, Enum):
    GENERAL = "general"
    EXAM = "exam"
    HOLIDAY = "holiday"
    EVENT = "event"
    ACADEMIC = "academic"
    EMERGENCY = "emergency"
    TRAINING = "training"
    MEETING = "meeting"


class TicketStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCategory(str, Enum):
    ATTENDANCE_CORRECTION = "attendance_correction"
    CERTIFICATE_REQUEST = "certificate_request"
    COURSE_QUERY = "course_query"
    GENERAL = "general"
    TECHNICAL = "technical"
    OTHER = "other"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"


class PaymentMethod(str, Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    OTHER = "other"


# ─── Core identity ───────────────────────────────────────────────────────────


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    name: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)

    users = relationship("User", back_populates="role")


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    # e.g. {"finance_access": true}

    role = relationship("Role", back_populates="users")
    staff_profile = relationship("Staff", back_populates="user", uselist=False)
    student_profile = relationship("Student", back_populates="user", uselist=False)
    parent_profile = relationship("Parent", back_populates="user", uselist=False)
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))

    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Staff(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    designation: Mapped[Optional[str]] = mapped_column(String(100))
    joining_date: Mapped[Optional[datetime]] = mapped_column(Date)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    max_daily_leads: Mapped[int] = mapped_column(Integer, default=50)
    is_available_for_leads: Mapped[bool] = mapped_column(Boolean, default=True)
    monthly_salary: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("branches.id"), index=True)

    user = relationship("User", back_populates="staff_profile")
    branch = relationship("Branch")
