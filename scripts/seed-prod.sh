# Seed entrypoint helper for production containers
# Usage (from repo root):
#   docker compose -f docker-compose.prod.yml --env-file .env.production exec api python -m app.db.seed
