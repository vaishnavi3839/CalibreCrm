from fastapi import APIRouter

from app.api.v1 import auth, branches, dashboard, followups, leads, ops, punch, staff, students

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(leads.router)
api_router.include_router(followups.router)
api_router.include_router(students.router)
api_router.include_router(ops.router)
api_router.include_router(staff.router)
api_router.include_router(punch.router)
api_router.include_router(branches.router)
