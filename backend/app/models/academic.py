from datetime import date, datetime, time
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    gen_uuid,
    LeadSource,
    LeadStatus,
    LeadTemperature,
    CallOutcome,
    FollowUpStatus,
    AttendanceStatus,
    AnnouncementType,
    TicketStatus,
    TicketCategory,
    NotificationChannel,
    PaymentMethod,
    TaskStatus,
    TaskPriority,
)


# ─── Academic structure ──────────────────────────────────────────────────────


class Branch(Base, TimestampMixin, SoftDeleteMixin):
    """Physical academy branch / campus for punch GPS and per-branch QR."""

    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geofence_radius_m: Mapped[float] = mapped_column(Float, default=200.0)
    punch_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    staff_start: Mapped[Optional[str]] = mapped_column(String(5), default="09:00")
    staff_end: Mapped[Optional[str]] = mapped_column(String(5), default="18:00")
    student_start: Mapped[Optional[str]] = mapped_column(String(5), default="09:00")
    student_end: Mapped[Optional[str]] = mapped_column(String(5), default="17:00")


class Course(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    duration_months: Mapped[Optional[int]] = mapped_column(Integer)
    has_flight_training: Mapped[bool] = mapped_column(Boolean, default=False)
    required_flight_hours: Mapped[Optional[float]] = mapped_column(Float)
    required_simulator_hours: Mapped[Optional[float]] = mapped_column(Float)
    fee_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))

    modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="course")
    subjects = relationship("Subject", back_populates="course")


class CourseModule(Base, TimestampMixin):
    __tablename__ = "course_modules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    duration_hours: Mapped[Optional[float]] = mapped_column(Float)

    course = relationship("Course", back_populates="modules")


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    module_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("course_modules.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)

    course = relationship("Course", back_populates="subjects")


class Batch(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    instructor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(50), default="active")

    course = relationship("Course", back_populates="batches")
    instructor = relationship("Staff")
    students = relationship("Student", back_populates="batch")
    timetable_slots = relationship("TimetableSlot", back_populates="batch")


class TimetableSlot(Base, TimestampMixin):
    __tablename__ = "timetable"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"), nullable=False)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("subjects.id"))
    instructor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[Optional[str]] = mapped_column(String(200))

    batch = relationship("Batch", back_populates="timetable_slots")


# ─── Students & Parents ──────────────────────────────────────────────────────


class Student(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    student_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, index=True)
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("courses.id"))
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("batches.id"))
    instructor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    dob: Mapped[Optional[date]] = mapped_column(Date)
    address: Mapped[Optional[str]] = mapped_column(Text)
    enrollment_date: Mapped[Optional[date]] = mapped_column(Date)
    academic_status: Mapped[str] = mapped_column(String(50), default="active")
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    course_progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    attendance_pct: Mapped[float] = mapped_column(Float, default=100.0)
    training_hours_completed: Mapped[float] = mapped_column(Float, default=0.0)
    simulator_hours_completed: Mapped[float] = mapped_column(Float, default=0.0)
    training_days_total: Mapped[int] = mapped_column(Integer, default=180)
    training_days_remaining: Mapped[int] = mapped_column(Integer, default=180)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("branches.id"), index=True)

    user = relationship("User", back_populates="student_profile")
    course = relationship("Course")
    batch = relationship("Batch", back_populates="students")
    instructor = relationship("Staff")
    branch = relationship("Branch")
    lead = relationship("Lead", foreign_keys=[lead_id], primaryjoin="Student.lead_id==Lead.id", viewonly=True)
    parents = relationship("ParentStudent", back_populates="student")


class Parent(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), default="parent")
    occupation: Mapped[Optional[str]] = mapped_column(String(100))

    user = relationship("User", back_populates="parent_profile")
    students = relationship("ParentStudent", back_populates="parent")


class ParentStudent(Base, TimestampMixin):
    __tablename__ = "parent_student"
    __table_args__ = (UniqueConstraint("parent_id", "student_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)

    parent = relationship("Parent", back_populates="students")
    student = relationship("Student", back_populates="parents")


# ─── CRM Leads ───────────────────────────────────────────────────────────────


class Lead(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_phone", "phone"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_status_temp", "status", "temperature"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    lead_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    age: Mapped[Optional[int]] = mapped_column(Integer)
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("courses.id"))
    source: Mapped[LeadSource] = mapped_column(SAEnum(LeadSource, name="lead_source"), nullable=False)
    assigned_staff_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    temperature: Mapped[Optional[LeadTemperature]] = mapped_column(
        SAEnum(LeadTemperature, name="lead_temperature")
    )
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_status"), default=LeadStatus.NEW, nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    conversion_status: Mapped[Optional[str]] = mapped_column(String(50))
    parent_involved: Mapped[bool] = mapped_column(Boolean, default=False)
    asked_about_admission: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_brochure: Mapped[bool] = mapped_column(Boolean, default=False)
    attended_counselling: Mapped[bool] = mapped_column(Boolean, default=False)
    campus_visit_done: Mapped[bool] = mapped_column(Boolean, default=False)
    registration_discussion: Mapped[bool] = mapped_column(Boolean, default=False)
    converted_student_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    updated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    message: Mapped[Optional[str]] = mapped_column(Text)

    course = relationship("Course")
    assigned_staff = relationship("Staff", foreign_keys=[assigned_staff_id])
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    followups = relationship("LeadFollowUp", back_populates="lead", cascade="all, delete-orphan")
    assignments = relationship("LeadAssignment", back_populates="lead", cascade="all, delete-orphan")


class LeadAssignment(Base, TimestampMixin):
    __tablename__ = "lead_assignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.id"), nullable=False)
    assigned_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    method: Mapped[str] = mapped_column(String(50), default="manual")  # manual | round_robin
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    lead = relationship("Lead", back_populates="assignments")
    staff = relationship("Staff")


class LeadActivity(Base, TimestampMixin):
    __tablename__ = "lead_activities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    staff_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # call, note, status_change, etc.
    call_outcome: Mapped[Optional[CallOutcome]] = mapped_column(SAEnum(CallOutcome, name="call_outcome"))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    temperature: Mapped[Optional[LeadTemperature]] = mapped_column(
        SAEnum(LeadTemperature, name="lead_temperature", create_constraint=False)
    )
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    lead = relationship("Lead", back_populates="activities")
    staff = relationship("Staff")


class LeadFollowUp(Base, TimestampMixin):
    __tablename__ = "lead_followups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False, index=True)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[FollowUpStatus] = mapped_column(
        SAEnum(FollowUpStatus, name="followup_status"), default=FollowUpStatus.PENDING
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    rescheduled_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("lead_followups.id"))

    lead = relationship("Lead", back_populates="followups")
    staff = relationship("Staff")


class LeadScoreRule(Base, TimestampMixin):
    __tablename__ = "lead_score_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    factor_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AssignmentCursor(Base, TimestampMixin):
    """Round-robin pointer for automatic lead distribution."""

    __tablename__ = "assignment_cursors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    strategy: Mapped[str] = mapped_column(String(50), default="round_robin", unique=True)
    last_staff_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
