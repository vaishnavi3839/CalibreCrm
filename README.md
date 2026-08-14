# Calibre Aviation Academy — CRM & Academy Management System

Production-oriented full-stack platform connecting the academy lifecycle:

**Lead → Telecaller → Follow-up → Counselling → Registration → Admission → Student → Attendance → Training → Exams → Documents/Certificates → Completion**

## Documentation

| Doc | What it is |
|-----|------------|
| [HOSTING_RAILWAY_RENDER.md](./HOSTING_RAILWAY_RENDER.md) | **Easiest: host on Railway or Render** (recommended) |
| [DEPLOY_NOW.md](./DEPLOY_NOW.md) | Docker/VPS deploy + Android Play Store |
| [HOSTING_FROM_SCRATCH.md](./HOSTING_FROM_SCRATCH.md) | Domain → own VPS → HTTPS (full beginner VPS guide) |
| [ABOUT.md](./ABOUT.md) | Short: what this project does |
| [DOCUMENTATION.md](./DOCUMENTATION.md) | Full technical + feature documentation |
| [USER_GUIDE.md](./USER_GUIDE.md) | Role-by-role how to use the app |
| [HOSTING.md](./HOSTING.md) | Deploy / host checklist |
| [WEB_AND_ANDROID.md](./WEB_AND_ANDROID.md) | Extra Android packaging notes |

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, JWT + RBAC |
| Database | PostgreSQL (production) / SQLite (local default) |
| Object storage | S3-compatible (MinIO locally) |
| Cache / queues | Redis (Docker Compose) |

## Quick start (local)

### 1. Environment

```bash
cp .env.example .env
```

Local development defaults to SQLite so you can run without Docker. For PostgreSQL + MinIO + Redis:

```bash
docker compose up -d
# then set DATABASE_URL in .env to the Postgres URLs from .env.example
```

### 2. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

### 3. Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

App: http://localhost:3000

## Demo logins

Password for all seeded users: `Password123!`

| Role | Email |
|------|-------|
| Super Admin | `superadmin@calibre.academy` |
| Admin | `admin@calibre.academy` |
| RM | `rm@calibre.academy` |
| Telecaller | `priya@calibre.academy` |
| Instructor | `instructor1@calibre.academy` |
| Accountant | `finance@calibre.academy` |
| Student | `rahul.student@calibre.academy` |
| Parent | `rahul.parent@calibre.academy` |

Full role walkthrough, daily report usage, and **how Admin adds staff**: see [USER_GUIDE.md](./USER_GUIDE.md).

## Role experiences

- **Admin / Super Admin** — Daily Academy Pulse, CRM, students, analytics
- **RM** — Lead assignment, staff performance, funnel, meetings
- **Telecaller** — Mobile-first CALL NOW workflow, follow-ups, targets, leaderboard
- **Instructor** — Students, attendance, exams (no CRM)
- **Accountant** — Finance module only (permission-gated)
- **Student / Parent** — Academic portals with **no fee/payment** and **no internal CRM** data

## Key API groups

- `POST /api/v1/auth/login|refresh|logout|forgot-password|reset-password`
- `GET /api/v1/dashboard` — role-specific payload
- `GET/POST /api/v1/leads` — CRM + telecaller workflow
- `POST /api/v1/leads/website-enquiry` — public website intake
- `GET /api/v1/followups` — today's follow-ups + overdue escalation
- `POST /api/v1/attendance` — marks attendance + parent absence alerts
- `GET /api/v1/certificates/verify/{code}` — public certificate verification
- `GET /api/v1/reports/conversion-funnel` / `lead-sources`

## Architecture notes

- RBAC enforced on backend (`app/core/permissions.py`) and frontend route guards
- Notification adapters are pluggable (in-app / email / SMS / WhatsApp / push) via env vars — no hard-coded provider secrets
- Lead scoring and staff performance points are configurable tables, not hard-coded constants
- Round-robin assignment is implemented; strategy hooks exist for course/location/workload later
- Object storage settings point at S3/MinIO for documents, certificates, receipts, and photos

## Tests

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

## Phased delivery status

| Phase | Status |
|-------|--------|
| 1 Foundation (auth, roles, schema, UI shell) | Done |
| 2 CRM (leads, assignment, call workflow, follow-ups, scoring, funnel) | Done (core) |
| 3 Staff (tasks, targets, performance, leaderboard) | Done (core) |
| 4 Students (profiles, attendance, exams, training, docs) | Done (core) |
| 5 Student/Parent portals + ID + tickets | Done (core) |
| 6 Communications architecture | Done (adapters + reminders model) |
| 7 Analytics & reports | Done (funnel + sources; export to expand) |
| 8 AI features | Scaffolded for future |

## Certificate verification

Seeded example: http://localhost:3000/verify/CAA-CPL-2026-00452
