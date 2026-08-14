# Railway — Click-by-click guide (from zero to your domain)

This is written for beginners. Follow **in order**. Do not skip steps.

You will end up with:

```text
https://crm.YOURDOMAIN.com   ← your real website
         │
         ├─ Web (Next.js frontend)
         └─ API (FastAPI backend) + Postgres database
```

Approx time: **45–90 minutes** the first time.

---

## Before you start — checklist of accounts

Create these if you don’t have them:

1. **GitHub** — https://github.com (your code is already at `vaishnavi3839/CalibreCrm`)
2. **Railway** — https://railway.com (sign up with GitHub)
3. **Domain** — buy from Namecheap / Hostinger / GoDaddy (optional for first test; required for a nice URL)

Also keep ready:

- Your **Gemini API key** (for grooming)
- A strong random password for JWT (you can make one later)

---

# PART 1 — Push the latest code to GitHub

On your Mac, open Terminal:

```bash
cd /Users/vaishnavip/Projects/crm
git status
```

If there are uncommitted Railway fix files, commit and push:

```bash
git add backend/railway.toml frontend/railway.toml backend/Dockerfile frontend/package.json RAILWAY.md
git commit -m "Add Railway configs for API and web services"
git push origin main
```

(Or ask Cursor: “commit and push”.)

Confirm on GitHub that the latest commit is visible:
https://github.com/vaishnavi3839/CalibreCrm

---

# PART 2 — Create a Railway project the RIGHT way

### Important

Your earlier build failed because Railway tried to deploy the **whole repo as one service**.

This project needs **3 things**:

1. **Postgres** database  
2. **API** service (`backend` folder)  
3. **Web** service (`frontend` folder)

---

## Step 2.1 — Open Railway

1. Go to https://railway.com  
2. Login with GitHub  
3. Click **New Project**

## Step 2.2 — Start empty (recommended)

Choose **Empty Project**  
(or if you already have `sweet-charisma / production`, open that project and continue)

Rename project (top left): e.g. **Calibre CRM**

---

## Step 2.3 — Delete the failed single service (if it exists)

If you still see **CalibreCrm** with red “Build failed”:

1. Click that service card  
2. Open **Settings**  
3. Scroll to bottom → **Delete Service**  
4. Confirm

You should now have an empty canvas (or only other healthy services).

---

# PART 3 — Add Postgres database

1. In the project canvas, click **+ Add**  
2. Click **Database**  
3. Click **PostgreSQL**  
4. Wait until it shows **Online** / healthy (green)

Click the Postgres card once → open **Variables** / **Connect** tab.

You will see a URL like:

```text
postgresql://postgres:xxxx@xxxxx.railway.app:5432/railway
```

**Keep this tab open.** You will copy it soon.

Make **two versions**:

### A) For FastAPI async (`DATABASE_URL`)
Change `postgresql://` → `postgresql+asyncpg://`

Example:

```text
postgresql+asyncpg://postgres:xxxx@xxxxx.railway.app:5432/railway
```

### B) For sync (`DATABASE_URL_SYNC`)
Keep normal:

```text
postgresql://postgres:xxxx@xxxxx.railway.app:5432/railway
```

> Tip: In Railway you can also click **Variable Reference** later and edit the scheme manually.

---

# PART 4 — Add the API service (backend)

## Step 4.1 — Create service from GitHub

1. Click **+ Add**  
2. Click **GitHub Repo**  
3. Select **`vaishnavi3839/CalibreCrm`**  
4. Railway creates a service (temporary name)

## Step 4.2 — Set Root Directory = backend

1. Click the new service  
2. Go to **Settings**  
3. Find **Root Directory**  
4. Set it to:

```text
backend
```

5. Save

This is the most important setting. Without it, build fails.

## Step 4.3 — Rename service

In Settings → Service name → rename to **`api`**

## Step 4.4 — Start command

In Settings → **Deploy** / **Custom Start Command**:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Step 4.5 — Add API variables

Go to **Variables** tab → **Raw Editor** (or add one by one).

Paste/add:

```text
APP_ENV=production
PYTHONPATH=.
JWT_SECRET_KEY=REPLACE_WITH_LONG_RANDOM_SECRET_32CHARS
DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:PORT/railway
DATABASE_URL_SYNC=postgresql://USER:PASS@HOST:PORT/railway
FRONTEND_URL=https://temporary-will-change-later
BACKEND_URL=https://temporary-will-change-later
CORS_ORIGINS=https://temporary-will-change-later
GEMINI_API_KEY=YOUR_GEMINI_KEY
GROOMING_VISION_MODEL=gemini-flash-latest
GOOGLE_CLIENT_ID=
```

Replace:

- `DATABASE_URL` / `DATABASE_URL_SYNC` with your real Postgres URLs  
- `JWT_SECRET_KEY` with a long random string  
- `GEMINI_API_KEY` with your key  

Generate JWT secret on your Mac:

```bash
openssl rand -hex 32
```

## Step 4.6 — Generate a public domain for API

1. API service → **Settings** → **Networking**  
2. Click **Generate Domain**  
3. Copy it, example:

```text
https://api-production-xxxx.up.railway.app
```

Save this as **API_URL**.

## Step 4.7 — Wait for successful deploy

Deployments tab should show **Success** (green).

If it fails:

- Confirm Root Directory is exactly `backend`
- Confirm start command uses `$PORT`
- Open **Build Logs** / **Deploy Logs** and copy the red error

---

# PART 5 — Add the Web service (frontend)

## Step 5.1 — Create another GitHub service

1. **+ Add** → **GitHub Repo**  
2. Select the **same** `CalibreCrm` repo again  
3. New service appears

## Step 5.2 — Root Directory = frontend

Settings → Root Directory:

```text
frontend
```

Rename service to **`web`**

## Step 5.3 — Build & start commands

**Build command:**

```bash
npm ci && npm run build
```

**Start command:**

```bash
npm run start -- --hostname 0.0.0.0 --port $PORT
```

## Step 5.4 — Web variables

```text
API_PROXY_TARGET=https://api-production-xxxx.up.railway.app
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
```

`API_PROXY_TARGET` must be your **API public domain** from Part 4.

## Step 5.5 — Generate web domain

Settings → Networking → **Generate Domain**

Example:

```text
https://web-production-xxxx.up.railway.app
```

Save this as **WEB_URL**.

## Step 5.6 — Wait for Success

Frontend build takes longer (2–5 minutes). Wait for green Success.

---

# PART 6 — Connect API ↔ Web correctly

Now go back to **api** service → Variables and update:

```text
FRONTEND_URL=https://web-production-xxxx.up.railway.app
BACKEND_URL=https://web-production-xxxx.up.railway.app
CORS_ORIGINS=https://web-production-xxxx.up.railway.app
```

Use your real **WEB_URL**.

Then **Redeploy** the API service (Deployments → Redeploy).

Why? So login/cookies/CORS allow your website.

---

# PART 7 — Seed the database (create Admin login)

1. Open **api** service  
2. Open **Shell** (or one-off command / “Run”)  
3. Run:

```bash
PYTHONPATH=. python -m app.db.seed
```

If Shell is not available on your plan, use Railway CLI later, or ask for help.

After seed, open:

```text
https://YOUR-WEB-URL/login
```

Login:

- Email: `admin@calibre.academy`
- Password: `Password123!`

If login works — **your web app is live.**  
Change the password after first login.

---

# PART 8 — Connect your own domain

Do this only after Railway URL login works.

Example domain: you bought `youracademy.com`  
We will use: **`crm.youracademy.com`**

---

## Step 8.1 — Add custom domain in Railway (Web service)

1. Open **web** service  
2. Settings → **Networking** → **Custom Domain**  
3. Type:

```text
crm.youracademy.com
```

4. Railway shows a DNS record to create. Usually one of:

### Common case — CNAME

| Type | Host/Name | Value / Target |
|------|-----------|----------------|
| CNAME | `crm` | `xxxx.up.railway.app` |

Copy **exactly** what Railway shows (don’t invent it).

---

## Step 8.2 — Add that record at your domain provider

### If domain is on Hostinger

1. Login Hostinger → Domains → your domain → **DNS / DNS Zone**  
2. Add record using Railway’s values  
3. Save

### If domain is on Namecheap

1. Domain List → Manage → **Advanced DNS**  
2. Add new record  
3. Save

### If domain is on GoDaddy

1. DNS Management → Add  
2. Save

### Notes

- Host is usually just `crm` (not the full domain)
- If Railway asks for an **A record** instead of CNAME, use the IP they give
- Remove any old conflicting `crm` records

---

## Step 8.3 — Wait for DNS + SSL

1. In Railway, custom domain status becomes **Active** / SSL ready  
2. Usually 5–30 minutes (sometimes longer)

Check from your Mac:

```bash
nslookup crm.youracademy.com
```

It should resolve (not “can’t find”).

Then open:

```text
https://crm.youracademy.com/login
```

---

## Step 8.4 — Update environment variables to your domain

In **api** variables, change to:

```text
FRONTEND_URL=https://crm.youracademy.com
BACKEND_URL=https://crm.youracademy.com
CORS_ORIGINS=https://crm.youracademy.com
```

Redeploy **api**.

(Optional) Also set Google Client ID origins to `https://crm.youracademy.com` in Google Cloud Console.

---

## Step 8.5 — (Optional) Custom domain for API too

Usually **not needed**, because the web app proxies `/api` to the API.

Only add API custom domain if you want something like `api.youracademy.com`.

---

# PART 9 — After website works (Android / Play Store)

1. Edit `mobile/capacitor.config.json`:

```json
"server": {
  "url": "https://crm.youracademy.com"
}
```

2. On Mac:

```bash
cd /Users/vaishnavip/Projects/crm/mobile
npm install
npx cap sync android
npx cap open android
```

3. Build signed AAB in Android Studio  
4. Upload to Google Play Console  

Details: `DEPLOY_NOW.md`

---

# Visual map of Railway canvas (final)

You should see 3 cards:

```text
[ Postgres ]     [ api ]     [ web ]
   database       backend     frontend
                  /backend    /frontend
```

- Click **web** domain → users open this  
- Click **api** → used by web via `API_PROXY_TARGET`  
- Postgres → used only by api  

---

# Troubleshooting (common)

## Build failed on first service
- Root Directory was empty (whole repo). Set `backend` or `frontend`.

## Frontend build fails on `next build --turbopack`
- Make sure latest code is pushed (we changed build to normal `next build`).

## Login page opens but API errors / can’t login
- `API_PROXY_TARGET` wrong  
- `CORS_ORIGINS` / `FRONTEND_URL` not updated to current web URL  
- Redeploy api after changing vars  

## Domain not working
- DNS record wrong host/value  
- Wait longer  
- Check Railway custom domain status  

## Database connection error
- `DATABASE_URL` must use `postgresql+asyncpg://`  
- `DATABASE_URL_SYNC` must use `postgresql://`  

## Seed command fails
- Run it inside **api** service, not web  
- `PYTHONPATH=.` must be set  

---

# Your personal fill-in sheet

Write these down as you go:

```text
API Railway URL:   https://________________________________
WEB Railway URL:   https://________________________________
Custom domain:     https://crm.____________________________

Postgres URL:      postgresql://____________________________
Async URL:         postgresql+asyncpg://____________________

JWT secret:        _________________________________________
Gemini key:        _________________________________________
```

---

# Exact order reminder

1. Push latest code to GitHub  
2. Railway project  
3. Delete failed single service  
4. Add Postgres  
5. Add API (`Root Directory = backend`)  
6. Generate API domain  
7. Add Web (`Root Directory = frontend`) + `API_PROXY_TARGET`  
8. Generate Web domain  
9. Update API CORS/FRONTEND_URL to Web URL  
10. Seed database  
11. Test login on Railway URL  
12. Add custom domain DNS  
13. Update env to custom domain  
14. (Later) Android app  

---

If you get stuck, send a screenshot of:

1. Railway canvas (all services)  
2. The failed service **Build Logs** (bottom red lines)  
3. Your domain DNS page  

and we fix the next step together.
