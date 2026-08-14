# Calibre Aviation Academy CRM — Documentation

## 1. Overview

This project is a **full-stack Academy Management + CRM** web application for Calibre Aviation Academy.

It covers the full lifecycle:

**Lead → Telecaller follow-up → Counselling → Registration → Admission → Student → QR Attendance → Training → Exams → Documents / Certificates → Completion**

The product is delivered as a **responsive web app**. The same hosted URL can also be wrapped as an **Android app** (see [WEB_AND_ANDROID.md](./WEB_AND_ANDROID.md)).

For a short “what it does” summary, see [ABOUT.md](./ABOUT.md).

---

## 2. Architecture

```text
┌─────────────────────┐         ┌──────────────────────┐
│  Next.js Frontend   │  /api/* │  FastAPI Backend      │
│  (Web / Android WV) │ ──────► │  JWT + RBAC           │
└─────────────────────┘         └──────────┬───────────┘
                                           │
                                ┌──────────▼───────────┐
                                │  PostgreSQL / SQLite │
                                │  Local uploads/     │
                                └──────────────────────┘
```

| Layer | Path | Stack |
|-------|------|--------|
| Frontend | `frontend/` | Next.js 15, TypeScript, Tailwind |
| Backend | `backend/` | FastAPI, SQLAlchemy async, JWT |
| DB | `.env` | SQLite local / Postgres production |
| Uploads | `backend/uploads/` | Selfies, avatars, documents |

Frontend proxies `/api/*`, `/health`, `/uploads/*` to the backend (`API_PROXY_TARGET`).

---

## 3. Roles & permissions

| Role | Key access |
|------|------------|
| Super Admin | Full system |
| Admin | Staff, students, branches, punch settings, salary, CRM |
| RM | Leads, assignment, performance |
| Telecaller | Only **assigned** leads, follow-ups, call workflow |
| Instructor | Students, class attendance, exams (no CRM) |
| Accountant | Finance module |
| Student | Own profile, attendance, documents (no fees/CRM) |
| Parent | Child attendance / alerts (no fees/CRM) |

**Login rule:** Only accounts created by Admin (or seeded) can sign in. Google Sign-In matches an existing email — it does **not** auto-create users.

Staff / students log in with the **email Admin entered** when adding them (plus temporary password shown on create).

---

## 4. Feature modules

### 4.1 CRM — Leads

- Create lead (name, phone, email, source, course…)
- Assignment modes:
  - **Auto (round robin)** → next available telecaller
  - **Manual** → pick staff
  - **Unassigned** → assign later
- Telecallers only see their own leads
- Import Excel supported
- Follow-ups & call activities

### 4.2 Branches

- Create multiple campuses (name, GPS, timings)
- Each branch has its own **punch QR** (downloadable)
- Staff / students are assigned a **punch branch**

### 4.3 QR Punch (attendance)

Flow for staff & students:

1. Open **QR Punch**
2. Scan branch QR (IN and OUT both need a fresh scan)
3. Popup: QR verified → scan face for grooming
4. Selfie + GPS → punch saved

Rules:

| Who | Late | Grooming fail |
|-----|------|----------------|
| Staff | Warnings; after 3 → half-day cut; after 7 → half salary | ₹500 from salary |
| Student | −1 day from 180 training days; parent notified | ₹500 fine; parent notified |

Notes:

- Bad/dark selfie → **retake, no fine**
- Real grooming fail (hair / appearance) → **₹500**
- Student IN punch updates attendance to **present** or **late** (not left as absent)

### 4.4 Grooming AI

- Uses Gemini (`GEMINI_API_KEY`) or OpenAI vision
- Checks hair, facial grooming, professional look
- Status visible on Punch Control for Admin

### 4.5 Salary

- Monthly base salary set when adding/editing staff
- Deductions for late + grooming
- Staff can view slip; Admin can download CSV

### 4.6 Students & Parents

- Student portal: attendance %, records, documents
- Parent portal: child’s presence / late / grooming alerts
- Fee/payment and CRM data are hidden from both

### 4.7 Other academy ops

- Courses, batches, exams, documents, certificates  
- Announcements, events, meetings, tasks  
- Daily pulse / analytics dashboards  

---

## 5. Important screens (URLs)

| Screen | Path |
|--------|------|
| Login | `/login` |
| Admin dashboard | `/app/admin` |
| Leads | `/app/leads` |
| Staff | `/app/staff` |
| Students | `/app/students` |
| Branches | `/app/branches` |
| QR Punch | `/app/punch` |
| Punch Control | `/app/punch/admin` |
| Salary | `/app/salary` |
| Student attendance | `/app/student/attendance` |

---

## 6. Backend API (high level)

Base: `/api/v1`

| Area | Examples |
|------|----------|
| Auth | `POST /auth/login`, `/auth/google`, `/auth/me` |
| Leads | `GET/POST /leads`, `/leads/{id}/assign`, `/auto-assign` |
| Staff | `GET/POST /staff` |
| Students | `GET/POST /students`, attendance endpoints |
| Branches | `GET/POST /branches`, QR rotate/download |
| Punch | `POST /punch`, `/punch/settings`, `/punch/presence`, `/punch/salary` |

Local API docs (dev only): `http://127.0.0.1:8000/api/docs`

---

## 7. Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Async DB URL |
| `JWT_SECRET_KEY` | Sign tokens (change in production) |
| `CORS_ORIGINS` | Allowed frontend origins |
| `GOOGLE_CLIENT_ID` | Backend Google verify |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Frontend Google button |
| `GEMINI_API_KEY` | Grooming vision |
| `API_PROXY_TARGET` | Next → API proxy target |

See `.env.example` and [HOSTING.md](./HOSTING.md).

---

## 8. Local development

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m app.db.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm install
npm run dev -- --port 3000 --hostname 127.0.0.1
```

Open: http://127.0.0.1:3000  

Demo password: `Password123!` (see README for emails)

---

## 9. Production hosting

Follow [HOSTING.md](./HOSTING.md):

1. Postgres + strong JWT  
2. `APP_ENV=production`  
3. Real CORS / domains  
4. Persistent uploads disk  
5. Gemini key for grooming  
6. Google OAuth production origins  

---

## 10. Project folder map

```text
crm/
├── ABOUT.md              ← what the project does
├── DOCUMENTATION.md      ← this file
├── USER_GUIDE.md         ← end-user / role guide
├── HOSTING.md            ← deploy checklist
├── WEB_AND_ANDROID.md    ← web + Android steps
├── README.md             ← developer quick start
├── backend/              ← FastAPI API
│   └── app/
│       ├── api/v1/       ← routes
│       ├── services/     ← business logic (punch, leads, grooming…)
│       ├── models/       ← database models
│       └── db/           ← session + seed
└── frontend/             ← Next.js UI
    └── src/app/          ← pages
```

---

## 11. Security notes

- Change default JWT secret before hosting  
- Do not ship demo passwords in production  
- Only provisioned emails can log in  
- Reset tokens are not returned in production API responses  
- `/uploads` is public by URL — treat selfie links carefully  

---

## 12. Support docs index

1. **What it does** → [ABOUT.md](./ABOUT.md)  
2. **Full documentation** → this file  
3. **How to use (roles)** → [USER_GUIDE.md](./USER_GUIDE.md)  
4. **Host as website** → [HOSTING.md](./HOSTING.md)  
5. **Web + Android packaging** → [WEB_AND_ANDROID.md](./WEB_AND_ANDROID.md)  
