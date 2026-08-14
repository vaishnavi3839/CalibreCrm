"""Seed realistic development data for Calibre Aviation Academy CRM."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, init_db
from app.models import (
    Announcement,
    AnnouncementType,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    Batch,
    Certificate,
    Course,
    CourseModule,
    Event,
    Exam,
    FollowUpStatus,
    Lead,
    LeadActivity,
    LeadFollowUp,
    LeadSource,
    LeadStatus,
    LeadTemperature,
    CallOutcome,
    Meeting,
    Notification,
    NotificationChannel,
    Parent,
    ParentStudent,
    PerformanceScoreRule,
    Role,
    Staff,
    StaffPerformanceDaily,
    StaffTarget,
    Student,
    Subject,
    Task,
    TaskPriority,
    TaskStatus,
    User,
    UserRole,
)
from app.services.scoring_service import ensure_default_score_rules


DEFAULT_PASSWORD = "Password123!"


async def get_or_create_role(db, role: UserRole, display: str) -> Role:
    existing = await db.scalar(select(Role).where(Role.name == role))
    if existing:
        existing.permissions = {p: True for p in ROLE_PERMISSIONS.get(role, [])}
        existing.display_name = display
        return existing
    obj = Role(
        name=role,
        display_name=display,
        description=f"{display} role",
        permissions={p: True for p in ROLE_PERMISSIONS.get(role, [])},
    )
    db.add(obj)
    await db.flush()
    return obj


async def create_user(
    db,
    *,
    email: str,
    full_name: str,
    role: Role,
    phone: str | None = None,
    extra: dict | None = None,
) -> User:
    existing = await db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        return existing
    user = User(
        email=email.lower(),
        full_name=full_name,
        phone=phone,
        password_hash=hash_password(DEFAULT_PASSWORD),
        role_id=role.id,
        extra_permissions=extra or {},
    )
    db.add(user)
    await db.flush()
    return user


async def seed() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        # Roles
        roles = {
            UserRole.SUPER_ADMIN: await get_or_create_role(db, UserRole.SUPER_ADMIN, "Super Admin"),
            UserRole.ADMIN: await get_or_create_role(db, UserRole.ADMIN, "Admin"),
            UserRole.RM: await get_or_create_role(db, UserRole.RM, "RM"),
            UserRole.TELECALLER: await get_or_create_role(db, UserRole.TELECALLER, "Telecaller / Counsellor"),
            UserRole.INSTRUCTOR: await get_or_create_role(db, UserRole.INSTRUCTOR, "Instructor / Faculty"),
            UserRole.ACCOUNTANT: await get_or_create_role(db, UserRole.ACCOUNTANT, "Accountant"),
            UserRole.STUDENT: await get_or_create_role(db, UserRole.STUDENT, "Student"),
            UserRole.PARENT: await get_or_create_role(db, UserRole.PARENT, "Parent"),
        }

        await ensure_default_score_rules(db)

        for key, name, points in [
            ("calls_completed", "Calls completed", 1),
            ("followup_completed", "Follow-up completed", 3),
            ("hot_lead", "Hot lead", 5),
            ("registration", "Registration", 15),
            ("admission", "Admission", 25),
        ]:
            if not await db.scalar(select(PerformanceScoreRule).where(PerformanceScoreRule.metric_key == key)):
                db.add(PerformanceScoreRule(metric_key=key, display_name=name, points=points))

        # Users
        super_admin = await create_user(
            db, email="superadmin@calibre.academy", full_name="Aarav Mehta", role=roles[UserRole.SUPER_ADMIN], phone="9000000001"
        )
        admin = await create_user(
            db, email="admin@calibre.academy", full_name="Neha Sharma", role=roles[UserRole.ADMIN], phone="9000000002"
        )
        rm = await create_user(
            db,
            email="rm@calibre.academy",
            full_name="Vikram Singh",
            role=roles[UserRole.RM],
            phone="9000000003",
            extra={"finance_access": True},
        )

        telecaller_users = []
        telecaller_names = [
            ("priya@calibre.academy", "Priya Nair", "9000000011"),
            ("arjun@calibre.academy", "Arjun Patel", "9000000012"),
            ("meera@calibre.academy", "Meera Iyer", "9000000013"),
            ("kabir@calibre.academy", "Kabir Khan", "9000000014"),
        ]
        for email, name, phone in telecaller_names:
            telecaller_users.append(await create_user(db, email=email, full_name=name, role=roles[UserRole.TELECALLER], phone=phone))

        instructor_users = [
            await create_user(db, email="instructor1@calibre.academy", full_name="Capt. Rohan Desai", role=roles[UserRole.INSTRUCTOR], phone="9000000021"),
            await create_user(db, email="instructor2@calibre.academy", full_name="Capt. Ananya Rao", role=roles[UserRole.INSTRUCTOR], phone="9000000022"),
        ]
        accountant = await create_user(
            db, email="finance@calibre.academy", full_name="Suresh Pillai", role=roles[UserRole.ACCOUNTANT], phone="9000000031"
        )

        # Staff profiles
        async def staff_for(user: User, code: str, dept: str, designation: str, available: bool = False) -> Staff:
            existing = await db.scalar(select(Staff).where(Staff.user_id == user.id))
            if existing:
                return existing
            s = Staff(
                user_id=user.id,
                employee_code=code,
                department=dept,
                designation=designation,
                joining_date=date(2024, 1, 15),
                languages=["English", "Hindi"],
                is_available_for_leads=available,
            )
            db.add(s)
            await db.flush()
            return s

        await staff_for(super_admin, "EMP-SA-001", "Management", "Super Admin")
        await staff_for(admin, "EMP-AD-001", "Operations", "Admin")
        rm_staff = await staff_for(rm, "EMP-RM-001", "CRM", "RM")
        tele_staff = []
        for i, u in enumerate(telecaller_users, start=1):
            tele_staff.append(await staff_for(u, f"EMP-TC-00{i}", "CRM", "Telecaller", available=True))
        instructors = []
        for i, u in enumerate(instructor_users, start=1):
            instructors.append(await staff_for(u, f"EMP-IN-00{i}", "Academics", "Instructor"))
        await staff_for(accountant, "EMP-FN-001", "Finance", "Accountant")

        # Courses
        course_defs = [
            ("CPL", "Commercial Pilot License", 18, True, 200, 40, 2500000),
            ("CC", "Cabin Crew", 6, False, None, None, 180000),
            ("GS", "Ground Staff", 4, False, None, None, 120000),
            ("AM", "Airport Management", 12, False, None, None, 350000),
            ("AH", "Aviation Hospitality", 6, False, None, None, 150000),
        ]
        courses = {}
        for code, name, months, flight, fh, sh, fee in course_defs:
            c = await db.scalar(select(Course).where(Course.code == code))
            if not c:
                c = Course(
                    code=code,
                    name=name,
                    description=f"{name} programme at Calibre Aviation Academy",
                    duration_months=months,
                    has_flight_training=flight,
                    required_flight_hours=fh,
                    required_simulator_hours=sh,
                    fee_amount=fee,
                )
                db.add(c)
                await db.flush()
                if code == "CPL":
                    for i, mod in enumerate(["Air Regulations", "Navigation", "Meteorology", "Technical General"]):
                        db.add(CourseModule(course_id=c.id, name=mod, order_index=i, duration_hours=40))
                        db.add(Subject(course_id=c.id, name=mod, code=f"CPL-{i+1}"))
            courses[code] = c

        await db.flush()

        batch_a = await db.scalar(select(Batch).where(Batch.code == "CPL-A-2026"))
        if not batch_a:
            batch_a = Batch(
                course_id=courses["CPL"].id,
                name="CPL Batch A",
                code="CPL-A-2026",
                start_date=date(2026, 1, 10),
                end_date=date(2027, 6, 30),
                instructor_id=instructors[0].id,
                capacity=25,
            )
            db.add(batch_a)
            await db.flush()

        # Students + parents
        student_specs = [
            ("Rahul Kumar", "rahul.student@calibre.academy", "9100000001", "CAA-STU-2026-001"),
            ("Sneha Reddy", "sneha.student@calibre.academy", "9100000002", "CAA-STU-2026-002"),
            ("Aditya Verma", "aditya.student@calibre.academy", "9100000003", "CAA-STU-2026-003"),
        ]
        students = []
        for name, email, phone, code in student_specs:
            existing_stu = await db.scalar(select(Student).where(Student.student_code == code))
            if existing_stu:
                students.append(existing_stu)
                continue
            u = await create_user(db, email=email, full_name=name, role=roles[UserRole.STUDENT], phone=phone)
            st = Student(
                user_id=u.id,
                student_code=code,
                course_id=courses["CPL"].id,
                batch_id=batch_a.id,
                instructor_id=instructors[0].id,
                dob=date(2005, 5, 12),
                address="Bengaluru, Karnataka",
                enrollment_date=date(2026, 1, 15),
                course_progress_pct=82 if "Rahul" in name else 65,
                attendance_pct=92 if "Rahul" in name else 88,
                training_hours_completed=84 if "Rahul" in name else 40,
            )
            db.add(st)
            await db.flush()
            students.append(st)

            parent_user = await create_user(
                db,
                email=email.replace("student", "parent"),
                full_name=f"Parent of {name.split()[0]}",
                role=roles[UserRole.PARENT],
                phone=phone.replace("910", "920"),
            )
            parent = Parent(user_id=parent_user.id, relationship_type="father")
            db.add(parent)
            await db.flush()
            db.add(ParentStudent(parent_id=parent.id, student_id=st.id, is_primary=True))

        # Leads (20+)
        lead_names = [
            ("Aisha Khan", "9800000001", LeadSource.INSTAGRAM, LeadTemperature.HOT, LeadStatus.INTERESTED),
            ("Rohan Gupta", "9800000002", LeadSource.WEBSITE, LeadTemperature.WARM, LeadStatus.FOLLOW_UP),
            ("Isha Malhotra", "9800000003", LeadSource.FACEBOOK, LeadTemperature.HOT, LeadStatus.COUNSELLING),
            ("Dev Sharma", "9800000004", LeadSource.GOOGLE_ADS, LeadTemperature.COLD, LeadStatus.CONTACTED),
            ("Anvi Joshi", "9800000005", LeadSource.REFERRAL, LeadTemperature.HOT, LeadStatus.CAMPUS_VISIT),
            ("Yash Thompson", "9800000006", LeadSource.WHATSAPP, LeadTemperature.WARM, LeadStatus.ASSIGNED),
            ("Kiara Das", "9800000007", LeadSource.YOUTUBE, None, LeadStatus.NEW),
            ("Neil Kapoor", "9800000008", LeadSource.WALK_IN, LeadTemperature.WARM, LeadStatus.INTERESTED),
            ("Pooja Sen", "9800000009", LeadSource.EVENT, LeadTemperature.HOT, LeadStatus.REGISTRATION),
            ("Harsh Vardhan", "9800000010", LeadSource.COLLEGE_VISIT, LeadTemperature.COLD, LeadStatus.NOT_INTERESTED),
            ("Mira Shah", "9800000011", LeadSource.INSTAGRAM, LeadTemperature.HOT, LeadStatus.FOLLOW_UP),
            ("Kunal Jain", "9800000012", LeadSource.WEBSITE, LeadTemperature.WARM, LeadStatus.CONTACTED),
            ("Riya Bose", "9800000013", LeadSource.REFERRAL, LeadTemperature.HOT, LeadStatus.INTERESTED),
            ("Varun Menon", "9800000014", LeadSource.GOOGLE_ADS, None, LeadStatus.NEW),
            ("Tara Fernandes", "9800000015", LeadSource.WHATSAPP, LeadTemperature.WARM, LeadStatus.ASSIGNED),
            ("Om Prakash", "9800000016", LeadSource.EXISTING_STUDENT, LeadTemperature.HOT, LeadStatus.COUNSELLING),
            ("Diya Nambiar", "9800000017", LeadSource.INSTAGRAM, LeadTemperature.COLD, LeadStatus.CONTACTED),
            ("Samir Qureshi", "9800000018", LeadSource.FACEBOOK, LeadTemperature.WARM, LeadStatus.FOLLOW_UP),
            ("Naina Pillai", "9800000019", LeadSource.WEBSITE, LeadTemperature.HOT, LeadStatus.INTERESTED),
            ("Farhan Ali", "9800000020", LeadSource.OTHER, None, LeadStatus.NEW),
            ("Leah George", "9800000021", LeadSource.YOUTUBE, LeadTemperature.WARM, LeadStatus.ASSIGNED),
            ("Vivek Chawla", "9800000022", LeadSource.WALK_IN, LeadTemperature.HOT, LeadStatus.CAMPUS_VISIT),
        ]

        existing_lead_count = await db.scalar(select(Lead.id).limit(1))
        if not existing_lead_count:
            now = datetime.now(timezone.utc)
            for i, (name, phone, source, temp, status) in enumerate(lead_names):
                staff = tele_staff[i % len(tele_staff)] if status != LeadStatus.NEW else None
                lead = Lead(
                    lead_code=f"CAA-L-2026-{i+1:05d}",
                    name=name,
                    phone=phone,
                    email=f"{name.lower().replace(' ', '.')}@example.com",
                    location=["Bengaluru", "Hyderabad", "Chennai", "Mumbai", "Pune"][i % 5],
                    age=18 + (i % 8),
                    course_id=courses[["CPL", "CC", "GS", "AM", "AH"][i % 5]].id,
                    source=source,
                    assigned_staff_id=staff.id if staff else None,
                    temperature=temp,
                    status=status,
                    score=40 + (i * 3) % 55,
                    notes="Interested in aviation career.",
                    last_contacted_at=now - timedelta(days=(i % 5)) if status != LeadStatus.NEW else None,
                    next_follow_up_at=now + timedelta(hours=2 + i) if status in {LeadStatus.FOLLOW_UP, LeadStatus.INTERESTED} else None,
                    parent_involved=i % 3 == 0,
                    asked_about_admission=i % 4 == 0,
                    requested_brochure=i % 2 == 0,
                    created_by_id=rm.id,
                )
                db.add(lead)
                await db.flush()
                db.add(
                    LeadActivity(
                        lead_id=lead.id,
                        staff_id=staff.id if staff else None,
                        activity_type="created",
                        feedback="Lead imported into CRM",
                    )
                )
                if staff and status != LeadStatus.NEW:
                    db.add(
                        LeadActivity(
                            lead_id=lead.id,
                            staff_id=staff.id,
                            activity_type="call",
                            call_outcome=CallOutcome.CONNECTED,
                            duration_seconds=180 + i * 10,
                            temperature=temp,
                            feedback="Discussed course duration and eligibility.",
                            created_at=now - timedelta(days=1),
                        )
                    )
                if lead.next_follow_up_at and staff:
                    db.add(
                        LeadFollowUp(
                            lead_id=lead.id,
                            staff_id=staff.id,
                            scheduled_at=lead.next_follow_up_at,
                            status=FollowUpStatus.PENDING,
                            notes="Call back regarding counselling slot",
                        )
                    )

        # Performance for today
        today = date.today()
        for i, s in enumerate(tele_staff):
            existing = await db.scalar(
                select(StaffPerformanceDaily).where(
                    StaffPerformanceDaily.staff_id == s.id, StaffPerformanceDaily.performance_date == today
                )
            )
            if not existing:
                db.add(
                    StaffPerformanceDaily(
                        staff_id=s.id,
                        performance_date=today,
                        leads_assigned=10 + i,
                        calls_completed=40 + i * 7,
                        connected_calls=22 + i * 3,
                        followups_completed=6 + i,
                        followups_missed=i,
                        hot_leads=3 + i,
                        warm_leads=5,
                        registrations=1 if i < 2 else 0,
                        admissions=1 if i == 0 else 0,
                        tasks_completed=4,
                        score=80 + i * 12,
                        badges=["Top Performer"] if i == 0 else [],
                    )
                )
                db.add(
                    StaffTarget(
                        staff_id=s.id,
                        period_type="daily",
                        period_start=today,
                        period_end=today,
                        metric_key="calls",
                        target_value=50,
                        current_value=40 + i * 7,
                        set_by_id=rm.id,
                    )
                )
                db.add(
                    StaffTarget(
                        staff_id=s.id,
                        period_type="daily",
                        period_start=today,
                        period_end=today,
                        metric_key="followups",
                        target_value=10,
                        current_value=6 + i,
                        set_by_id=rm.id,
                    )
                )

        # Tasks
        if not await db.scalar(select(Task.id).limit(1)):
            db.add(Task(title="Call Aisha Khan", description="Hot lead follow-up", assigned_to_id=telecaller_users[0].id, created_by_id=rm.id, priority=TaskPriority.HIGH, status=TaskStatus.PENDING, due_at=datetime.now(timezone.utc) + timedelta(hours=3)))
            db.add(Task(title="Review staff performance", assigned_to_id=rm.id, created_by_id=admin.id, priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING, due_at=datetime.now(timezone.utc) + timedelta(days=1)))
            db.add(Task(title="Enter exam marks", assigned_to_id=instructor_users[0].id, created_by_id=admin.id, priority=TaskPriority.HIGH, status=TaskStatus.PENDING, due_at=datetime.now(timezone.utc) + timedelta(days=2)))

        # Announcements / events / meetings
        if not await db.scalar(select(Announcement.id).limit(1)):
            db.add(
                Announcement(
                    title="Independence Day Holiday",
                    description="Academy will remain closed on 15 August 2026.",
                    announcement_type=AnnouncementType.HOLIDAY,
                    event_date=date(2026, 8, 15),
                    audience={"roles": ["student", "parent", "staff", "all"]},
                    publish_at=datetime.now(timezone.utc) - timedelta(days=1),
                    created_by_id=admin.id,
                )
            )
            db.add(
                Announcement(
                    title="Exam Tomorrow — Air Regulations",
                    description="CPL Batch A students: Air Regulations exam at 10:00 AM.",
                    announcement_type=AnnouncementType.EXAM,
                    event_date=date.today() + timedelta(days=1),
                    audience={"roles": ["student", "parent", "instructor"]},
                    publish_at=datetime.now(timezone.utc),
                    created_by_id=admin.id,
                )
            )
            db.add(
                Event(
                    title="Parent Meeting",
                    description="Quarterly parent interaction",
                    event_type="parent_meeting",
                    start_at=datetime.now(timezone.utc) + timedelta(days=5),
                    location="Main Auditorium",
                    audience={"roles": ["parent", "admin"]},
                    created_by_id=admin.id,
                )
            )
            db.add(
                Meeting(
                    title="Weekly CRM Sync",
                    description="Review hot leads and conversions",
                    agenda="1. Hot leads\n2. Missed follow-ups\n3. Admissions pipeline",
                    start_at=datetime.now(timezone.utc) + timedelta(days=1, hours=2),
                    duration_minutes=45,
                    zoom_link="https://zoom.us/j/calibre-crm-weekly",
                    audience={"roles": ["rm", "telecaller", "admin"]},
                    created_by_id=rm.id,
                )
            )

        # Attendance sample
        if students and not await db.scalar(select(AttendanceSession.id).limit(1)):
            session = AttendanceSession(batch_id=batch_a.id, session_date=date.today(), marked_by_id=instructors[0].id)
            db.add(session)
            await db.flush()
            for i, st in enumerate(students):
                status = AttendanceStatus.ABSENT if i == 2 else AttendanceStatus.PRESENT
                db.add(AttendanceRecord(session_id=session.id, student_id=st.id, status=status))

        # Exam + certificate
        if not await db.scalar(select(Exam.id).limit(1)):
            db.add(
                Exam(
                    title="Air Regulations Midterm",
                    batch_id=batch_a.id,
                    exam_date=date.today() + timedelta(days=1),
                    venue="Exam Hall 1",
                    instructions="Bring student ID. No electronic devices.",
                    max_marks=100,
                    created_by_id=admin.id,
                )
            )
        if students and not await db.scalar(select(Certificate.id).limit(1)):
            db.add(
                Certificate(
                    certificate_code="CAA-CPL-2026-00452",
                    student_id=students[0].id,
                    course_id=courses["CPL"].id,
                    title="Commercial Pilot Training — Module Completion",
                    completion_date=date.today(),
                    qr_payload="CAA-CPL-2026-00452",
                    issued_by_id=admin.id,
                )
            )

        # Notifications
        if not await db.scalar(select(Notification.id).limit(1)):
            db.add(Notification(user_id=telecaller_users[0].id, title="New lead assigned", body="Aisha Khan has been assigned to you.", category="lead_assigned", channel=NotificationChannel.IN_APP, delivery_status="delivered"))
            db.add(Notification(user_id=rm.id, title="You are today's top performer context", body="Monitor Priya's conversion streak.", category="performance", channel=NotificationChannel.IN_APP, delivery_status="delivered"))
            if students:
                db.add(Notification(user_id=students[0].user_id, title="Exam tomorrow", body="Air Regulations exam is scheduled tomorrow at 10:00 AM.", category="exam", channel=NotificationChannel.IN_APP, delivery_status="delivered"))

        await db.commit()
        print("Seed completed successfully.")
        print("Login with any seeded user and password:", DEFAULT_PASSWORD)
        print("Examples: admin@calibre.academy | rm@calibre.academy | priya@calibre.academy | rahul.student@calibre.academy | rahul.parent@calibre.academy")


if __name__ == "__main__":
    asyncio.run(seed())
