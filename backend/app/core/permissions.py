from typing import Optional

from app.models.base import UserRole

# Permission catalog used by Role.permissions JSON and route guards.
PERMISSIONS = {
    "users.manage": "Manage users",
    "staff.manage": "Manage staff",
    "students.manage": "Manage students",
    "parents.manage": "Manage parents",
    "leads.view": "View leads",
    "leads.manage": "Manage leads",
    "leads.assign": "Assign leads",
    "leads.import": "Import leads",
    "leads.convert": "Convert leads",
    "followups.view": "View follow-ups",
    "followups.manage": "Manage follow-ups",
    "courses.manage": "Manage courses",
    "batches.manage": "Manage batches",
    "attendance.view": "View attendance",
    "attendance.mark": "Mark attendance",
    "exams.manage": "Manage exams",
    "exams.marks": "Enter exam marks",
    "training.manage": "Manage training",
    "documents.manage": "Manage documents",
    "certificates.manage": "Manage certificates",
    "announcements.manage": "Manage announcements",
    "events.manage": "Manage events",
    "meetings.manage": "Manage meetings",
    "tasks.manage": "Manage tasks",
    "tasks.own": "Own tasks",
    "targets.manage": "Manage targets",
    "performance.view_all": "View all performance",
    "performance.view_own": "View own performance",
    "finance.view": "View finance",
    "finance.manage": "Manage finance",
    "reports.view": "View reports",
    "audit.view": "View audit logs",
    "config.manage": "Manage system config",
    "notifications.view": "View notifications",
    "tickets.manage": "Manage support tickets",
    "tickets.create": "Create support tickets",
    "portal.student": "Student portal",
    "portal.parent": "Parent portal",
}

ROLE_PERMISSIONS: dict[UserRole, list[str]] = {
    UserRole.SUPER_ADMIN: list(PERMISSIONS.keys()),
    UserRole.ADMIN: [
        "staff.manage",
        "students.manage",
        "parents.manage",
        "leads.view",
        "leads.manage",
        "leads.assign",
        "leads.import",
        "leads.convert",
        "followups.view",
        "followups.manage",
        "courses.manage",
        "batches.manage",
        "attendance.view",
        "attendance.mark",
        "exams.manage",
        "exams.marks",
        "training.manage",
        "documents.manage",
        "certificates.manage",
        "announcements.manage",
        "events.manage",
        "meetings.manage",
        "tasks.manage",
        "targets.manage",
        "performance.view_all",
        "reports.view",
        "notifications.view",
        "tickets.manage",
        # finance only if explicitly granted via user.extra_permissions
    ],
    UserRole.RM: [
        "leads.view",
        "leads.manage",
        "leads.assign",
        "leads.import",
        "leads.convert",
        "followups.view",
        "followups.manage",
        "tasks.manage",
        "targets.manage",
        "performance.view_all",
        "meetings.manage",
        "reports.view",
        "notifications.view",
        "staff.manage",
        # authorized payment view via extra_permissions.finance_access
    ],
    UserRole.TELECALLER: [
        "leads.view",
        "followups.view",
        "followups.manage",
        "tasks.own",
        "performance.view_own",
        "notifications.view",
        "leads.convert",  # when authorized by workflow
    ],
    UserRole.INSTRUCTOR: [
        "students.manage",
        "attendance.view",
        "attendance.mark",
        "exams.manage",
        "exams.marks",
        "training.manage",
        "tasks.own",
        "notifications.view",
        "batches.manage",
    ],
    UserRole.ACCOUNTANT: [
        "finance.view",
        "finance.manage",
        "students.manage",
        "reports.view",
        "notifications.view",
    ],
    UserRole.STUDENT: [
        "portal.student",
        "notifications.view",
        "tickets.create",
        "attendance.view",
    ],
    UserRole.PARENT: [
        "portal.parent",
        "notifications.view",
        "tickets.create",
        "attendance.view",
    ],
}


def role_has_permission(role: UserRole, permission: str, extra: Optional[dict] = None) -> bool:
    perms = set(ROLE_PERMISSIONS.get(role, []))
    extra = extra or {}
    if extra.get("finance_access"):
        perms.update({"finance.view", "finance.manage"})
    if extra.get("permissions"):
        perms.update(extra["permissions"])
    if permission in perms:
        return True
    # Super admin always true via ROLE_PERMISSIONS, but keep explicit fallback
    return role == UserRole.SUPER_ADMIN
