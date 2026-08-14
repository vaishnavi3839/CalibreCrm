from datetime import date, datetime, time
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    gen_uuid,
    AttendanceStatus,
    AnnouncementType,
    TicketStatus,
    TicketCategory,
    NotificationChannel,
    PaymentMethod,
    TaskStatus,
    TaskPriority,
)


# ─── Attendance ──────────────────────────────────────────────────────────────


class AttendanceSession(Base, TimestampMixin):
    __tablename__ = "attendance_sessions"
    __table_args__ = (UniqueConstraint("batch_id", "session_date", "subject_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"), nullable=False)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("subjects.id"))
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    marked_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance_sessions.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus, name="attendance_status"), nullable=False
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text)

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student")


# ─── Exams & Training ────────────────────────────────────────────────────────


class Exam(Base, TimestampMixin):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("subjects.id"))
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[time]] = mapped_column(Time)
    end_time: Mapped[Optional[time]] = mapped_column(Time)
    venue: Mapped[Optional[str]] = mapped_column(String(200))
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Float, default=100.0)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    results = relationship("ExamResult", back_populates="exam", cascade="all, delete-orphan")


class ExamResult(Base, TimestampMixin):
    __tablename__ = "exam_results"
    __table_args__ = (UniqueConstraint("exam_id", "student_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[Optional[str]] = mapped_column(String(10))
    result: Mapped[str] = mapped_column(String(20), default="pass")  # pass | fail | absent
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    entered_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    exam = relationship("Exam", back_populates="results")
    student = relationship("Student")


class TrainingRecord(Base, TimestampMixin):
    __tablename__ = "training_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    training_type: Mapped[str] = mapped_column(String(50), nullable=False)  # flight | simulator | practical
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours: Mapped[float] = mapped_column(Float, nullable=False)
    instructor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.id"))
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    aircraft_or_device: Mapped[Optional[str]] = mapped_column(String(100))

    student = relationship("Student")
    instructor = relationship("Staff")


class AcademicProgress(Base, TimestampMixin):
    __tablename__ = "academic_progress"
    __table_args__ = (UniqueConstraint("student_id", "module_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("course_modules.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="upcoming")  # completed | in_progress | upcoming
    completion_pct: Mapped[float] = mapped_column(Float, default=0.0)
    instructor_remarks: Mapped[Optional[str]] = mapped_column(Text)
    updated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


# ─── Documents & Certificates ────────────────────────────────────────────────


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("students.id"), index=True)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    can_student_download: Mapped[bool] = mapped_column(Boolean, default=True)
    can_parent_download: Mapped[bool] = mapped_column(Boolean, default=True)
    uploaded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    certificate_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    completion_date: Mapped[date] = mapped_column(Date, nullable=False)
    file_key: Mapped[Optional[str]] = mapped_column(String(500))
    qr_payload: Mapped[str] = mapped_column(String(500), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    issued_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

    student = relationship("Student")
    course = relationship("Course")


# ─── Communications ──────────────────────────────────────────────────────────


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    announcement_type: Mapped[AnnouncementType] = mapped_column(
        SAEnum(AnnouncementType, name="announcement_type"), default=AnnouncementType.GENERAL
    )
    event_date: Mapped[Optional[date]] = mapped_column(Date)
    event_time: Mapped[Optional[time]] = mapped_column(Time)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    audience: Mapped[dict] = mapped_column(JSON, default=dict)
    # e.g. {"roles": ["student"], "course_ids": [], "batch_ids": [], "user_ids": []}
    attachment_key: Mapped[Optional[str]] = mapped_column(String(500))
    publish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    audience: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    agenda: Mapped[Optional[str]] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    zoom_link: Mapped[Optional[str]] = mapped_column(String(500))
    audience: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    decisions: Mapped[Optional[str]] = mapped_column(Text)
    action_items: Mapped[list] = mapped_column(JSON, default=list)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="general")
    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel, name="notification_channel"),
        default=NotificationChannel.IN_APP,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    link: Mapped[Optional[str]] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    delivery_status: Mapped[str] = mapped_column(String(50), default="pending")


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # follow_up | exam | meeting | task | attendance | event | custom
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    channels: Mapped[list] = mapped_column(JSON, default=list)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | sent | cancelled
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ─── Tasks, Targets, Performance ─────────────────────────────────────────────


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, name="task_priority"), default=TaskPriority.MEDIUM
    )
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status"), default=TaskStatus.PENDING
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    related_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("leads.id"))
    related_student_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("students.id"))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class StaffTarget(Base, TimestampMixin):
    __tablename__ = "staff_targets"
    __table_args__ = (UniqueConstraint("staff_id", "period_type", "period_start", "metric_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.id"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # daily | weekly | monthly
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(50), nullable=False)
    # calls | followups | hot_leads | counselling | registrations | admissions
    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, default=0)
    set_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class PerformanceScoreRule(Base, TimestampMixin):
    __tablename__ = "performance_score_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    metric_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class StaffPerformanceDaily(Base, TimestampMixin):
    __tablename__ = "staff_performance_daily"
    __table_args__ = (UniqueConstraint("staff_id", "performance_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.id"), nullable=False, index=True)
    performance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    leads_assigned: Mapped[int] = mapped_column(Integer, default=0)
    calls_completed: Mapped[int] = mapped_column(Integer, default=0)
    connected_calls: Mapped[int] = mapped_column(Integer, default=0)
    followups_completed: Mapped[int] = mapped_column(Integer, default=0)
    followups_missed: Mapped[int] = mapped_column(Integer, default=0)
    hot_leads: Mapped[int] = mapped_column(Integer, default=0)
    warm_leads: Mapped[int] = mapped_column(Integer, default=0)
    registrations: Mapped[int] = mapped_column(Integer, default=0)
    admissions: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)
    badges: Mapped[list] = mapped_column(JSON, default=list)


# ─── Payments (internal only) ────────────────────────────────────────────────


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    payment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # registration | admission | course | installment
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method"), default=PaymentMethod.UPI
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100))
    receipt_key: Mapped[Optional[str]] = mapped_column(String(500))
    outstanding_after: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    recorded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


# ─── Support & Audit ─────────────────────────────────────────────────────────


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    ticket_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("students.id"))
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("parents.id"))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[TicketCategory] = mapped_column(
        SAEnum(TicketCategory, name="ticket_category"), default=TicketCategory.GENERAL
    )
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, name="task_priority", create_constraint=False),
        default=TaskPriority.MEDIUM,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status"), default=TicketStatus.OPEN
    )
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    attachment_key: Mapped[Optional[str]] = mapped_column(String(500))
    response: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_config"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[Optional[str]] = mapped_column(Text)


class PunchType(str, Enum):
    IN = "in"
    OUT = "out"


class DeductionType(str, Enum):
    HALF_DAY = "half_day"
    HALF_SALARY = "half_salary"
    GROOMING_FINE = "grooming_fine"
    OTHER = "other"


class AcademyPunchQr(Base, TimestampMixin):
    """Shared academy QR token for in/out punch (rotated by Admin)."""

    __tablename__ = "academy_punch_qr"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), default="Academy Punch")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PunchEvent(Base, TimestampMixin):
    __tablename__ = "punch_events"
    __table_args__ = (Index("ix_punch_user_date", "user_id", "punch_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    punch_type: Mapped[PunchType] = mapped_column(SAEnum(PunchType, name="punch_type"), nullable=False)
    punched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    punch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    accuracy_m: Mapped[Optional[float]] = mapped_column(Float)
    on_campus: Mapped[Optional[bool]] = mapped_column(Boolean)
    distance_m: Mapped[Optional[float]] = mapped_column(Float)
    selfie_url: Mapped[Optional[str]] = mapped_column(String(500))
    grooming_ok: Mapped[Optional[bool]] = mapped_column(Boolean)
    grooming_notes: Mapped[Optional[str]] = mapped_column(String(255))
    qr_token: Mapped[Optional[str]] = mapped_column(String(64))
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("branches.id"), index=True)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)

    user = relationship("User")
    branch = relationship("Branch")


class LateWarning(Base, TimestampMixin):
    __tablename__ = "late_warnings"
    __table_args__ = (UniqueConstraint("user_id", "warning_date", name="uq_late_warning_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    warning_date: Mapped[date] = mapped_column(Date, nullable=False)
    month_key: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    punch_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("punch_events.id"))
    note: Mapped[Optional[str]] = mapped_column(String(255))


class PayrollDeduction(Base, TimestampMixin):
    __tablename__ = "payroll_deductions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.id"), nullable=False, index=True)
    month_key: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    deduction_type: Mapped[DeductionType] = mapped_column(
        SAEnum(DeductionType, name="deduction_type"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    punch_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("punch_events.id"))
    applied_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class MonthlySalarySlip(Base, TimestampMixin):
    __tablename__ = "monthly_salary_slips"
    __table_args__ = (UniqueConstraint("staff_id", "month_key", name="uq_salary_slip_month"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.id"), nullable=False, index=True)
    month_key: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    base_salary: Mapped[float] = mapped_column(Float, nullable=False)
    total_deductions: Mapped[float] = mapped_column(Float, default=0.0)
    net_salary: Mapped[float] = mapped_column(Float, nullable=False)
    late_days: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    present_days: Mapped[int] = mapped_column(Integer, default=0)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
