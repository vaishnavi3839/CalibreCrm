#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "→ Seeding / ensuring backend deps"
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3.12 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi
PYTHONPATH=. python -m app.db.seed

echo "→ Starting API on :8000"
PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
