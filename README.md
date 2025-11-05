
# VM Migrator – Full Fix (Backend + Frontend + Worker)
# migration Vmware Workload to Proxmox and create Batch Job - 
A clean, runnable stack:
- **Backend**: FastAPI + SQLAlchemy + JWT
- **Worker**: Celery + Redis (orchestrates VMware → Proxmox migration plan)
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

- Use the `/api/providers/{id}/sync` endpoint (exposed in the UI) to pull vCenter inventory and Proxmox nodes before queuing jobs.
- Review `execute_migration_job` in `backend/app/tasks.py` to replace the placeholder export/convert/upload steps with production tooling.
- Recent provider and job activity is captured under **Logs** in the UI via `/api/logs/system`.
- Move secrets into a real `.env` for non-dev.
- Add Alembic for migrations if you expand models.
# vm-migrator-v2
