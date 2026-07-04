# Octane

A small, secure, future-proof Python messaging server. Instagram-style DMs, no media, end-to-end-style envelope encryption at rest, WebSockets for live push, deployable on Render's free tier.

## Features (v1)

- Signup / login / logout with JWT access + refresh (rotating, multi-device)
- User profiles + username search
- Asymmetric follow / unfollow
- 1:1 encrypted direct chat
- Typing indicators, read receipts, presence (over WebSocket)
- Server-decrypts-on-delivery (envelope encryption with libsodium)

## Stack

- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2.0 (async) + aiosqlite + Alembic
- PyNaCl (XChaCha20-Poly1305 envelope)
- Argon2id (passwords), PyJWT (tokens)
- structlog (JSON logs)
- SQLite (single file)

## Quick start (local)

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Generate secrets (copy output into .env)
python scripts/genkey.py

# 3. Create local config
cp .env.example .env
# Paste the generated JWT_SECRET and MASTER_KEY into .env

# 4. Initialize the database
alembic upgrade head

# 5. Run the server
uvicorn app.main:app --reload
```

The server listens on `http://localhost:8000`. Visit `/health` to confirm it's up.

## Render deploy

1. Push this repo to GitHub.
2. Create a new Render Web Service from the repo.
3. Render will read `render.yaml` and provision the free-tier service.
4. In the dashboard, set:
   - `ALLOWED_ORIGINS` to your real frontend origin (e.g. `https://your-app.onrender.com`).
5. Render will generate `JWT_SECRET` and `MASTER_KEY` automatically (or you can paste your own).
6. Wait for the deploy. `https://<app>.onrender.com/health` should return `{"status":"ok","db":"ok"}`.

> **Important: SQLite on Render free tier is ephemeral.** Every redeploy or restart may wipe the SQLite file. Run `python scripts/backup_db.py` before any redeploy, or wire it into a Render Cron Job for daily backups. See "Backups" below.

## Backups

```bash
pip install -r requirements-backup.txt

# Configure these in .env or your shell:
#   BACKUP_S3_URL=s3://your-bucket
#   AWS_ACCESS_KEY_ID=...
#   AWS_SECRET_ACCESS_KEY=...
#   AWS_ENDPOINT_URL=https://s3.us-west-002.backblazeb2.com  # B2 example
#   AWS_REGION=us-west-002

python scripts/backup_db.py   # push today's DB
python scripts/restore_db.py  # pull the latest backup
```

Backblaze B2's free tier (10GB) is more than enough for a small SQLite file.

## Project layout

```
app/
  api/         # HTTP routes
  ws/          # WebSocket layer
  core/        # cross-cutting (crypto, security, ratelimit)
  db/          # SQLAlchemy models + engine
  schemas/     # Pydantic request/response DTOs
  services/    # business logic
alembic/       # migrations
scripts/       # genkey, backup, restore
tests/         # pytest suite
```

## When you outgrow SQLite

If 60 users becomes 6000, or write contention becomes a problem:

1. Provision a managed Postgres (Render has one for $7/mo, or Neon/Supabase free).
2. Change `DATABASE_URL` to `postgresql+asyncpg://...`.
3. The SQLAlchemy code is identical — same models, same queries. Alembic migrations work unchanged.

That's the only change needed.

## License

Private.
