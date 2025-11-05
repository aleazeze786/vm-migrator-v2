
# VM Migrator – Full Fix (Backend + Frontend + Worker)

A clean, runnable stack:
- **Backend**: FastAPI + SQLAlchemy + JWT
- **Worker**: Celery + Redis (fake migration task that updates DB progress)
- **DB**: Postgres
- **Frontend**: Vite + React + TypeScript (login, list VMs, start migrations, live job progress)
- **Compose**: one command brings it all up

## Quick start (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8000 (docs at `/docs`)
- UI:  http://localhost:5173
- Default login: `admin` / `admin`

## Manual dev

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg2://vmuser:vmpass@localhost:5432/vmdb'
export CELERY_BROKER_URL='redis://localhost:6379/0'
export CELERY_RESULT_BACKEND='redis://localhost:6379/0'
uvicorn app.main:app --reload
```

Worker:
```bash
celery -A app.celery_app.celery worker -l info
```

### Frontend
```bash
cd frontend
cp .env.example .env   # optional
npm ci
npm run dev
```

## Notes

- Replace `fake_migrate_vm` with real VMware/Proxmox logic; keep DB updates and exception handling.
- Move secrets into a real `.env` for non-dev.
- Add Alembic for migrations if you expand models.
# vm-migrator-v2
