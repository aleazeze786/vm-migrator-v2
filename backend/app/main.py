from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import timedelta
from pydantic import BaseModel
from typing import List, Optional
from passlib.exc import UnknownHashError

from .database import Base, engine, get_db
from .models import User, Job, Provider, ProviderType
from .schemas import (
    Token, UserOut, JobCreate, JobOut,
    ProviderCreate, ProviderOut, BatchJobCreate
)
from .security import create_access_token, get_password_hash, verify_password
from .config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, API_TITLE
from .tasks import fake_migrate_vm
from fastapi.responses import StreamingResponse
import asyncio
from sqlalchemy import select, desc
from .models import JobLog

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title=API_TITLE)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(bind=engine)

def seed_admin(db: Session):
    existing = db.query(User).filter(User.username == "admin").first()
    if not existing:
        db.add(User(username="admin", hashed_password=get_password_hash("admin"), role="admin"))
        db.commit()
        return

    # Rehash admin to current scheme if needed (e.g., legacy bcrypt hash)
    try:
        ok = verify_password("admin", existing.hashed_password)
    except UnknownHashError:
        ok = False

    if not ok:
        existing.hashed_password = get_password_hash("admin")
        db.commit()

@app.on_event("startup")
def on_startup():
    with next(get_db()) as db:
        seed_admin(db)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# ---------- JSON login ----------
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/token", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

# ---------- Providers ----------
@app.post("/api/providers", response_model=ProviderOut)
def create_provider(payload: ProviderCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = Provider(name=payload.name, type=ProviderType(payload.type), api_url=payload.api_url,
                 username=payload.username, secret=payload.secret, verify_ssl=payload.verify_ssl)
    db.add(p); db.commit(); db.refresh(p)
    return p

@app.get("/api/providers", response_model=List[ProviderOut])
def list_providers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Provider).order_by(Provider.id.desc()).all()

@app.delete("/api/providers/{pid}")
def delete_provider(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Provider, pid)
    if not p: raise HTTPException(404, "Provider not found")
    db.delete(p); db.commit()
    return {"ok": True}

# ---------- VM discovery (stubbed per provider type) ----------
@app.get("/api/vms", response_model=List[str])
def list_vms(provider_id: Optional[int] = Query(None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if provider_id:
        p = db.get(Provider, provider_id)
        if not p: raise HTTPException(404, "Provider not found")
        if p.type == ProviderType.proxmox:
            return [f"pmx-{i:02d}" for i in range(1, 21)]
        if p.type == ProviderType.vcenter:
            return [f"vc-{i:02d}" for i in range(1, 21)]
    return ["vm-win-2016", "vm-ubuntu-22", "vm-sql-01"]

# ---------- Jobs ----------
@app.post("/api/jobs", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = Job(vm_name=payload.vm_name, status="queued", progress=0)
    db.add(job); db.commit(); db.refresh(job)
    fake_migrate_vm.apply_async(args=[job.id, job.vm_name])
    return job

@app.post("/api/jobs/batch", response_model=List[JobOut])
def create_batch(payload: BatchJobCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(Provider, payload.provider_id):
        raise HTTPException(404, "Provider not found")
    out = []
    for name in payload.vm_names:
        j = Job(vm_name=name, status="queued", progress=0)
        db.add(j); db.commit(); db.refresh(j)
        fake_migrate_vm.apply_async(args=[j.id, j.vm_name])
        out.append(j)
    return out

@app.get("/api/jobs", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Job).order_by(Job.id.desc()).all()

@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "Job not found")
    return job
async def get_user_from_token_query(token: str, db: Session) -> User:
    # validate the same way as get_current_user does (but with token param)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
@app.get("/api/jobs/{job_id}/logs")
def job_logs(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(JobLog).where(JobLog.job_id == job_id).order_by(JobLog.id.asc())
    ).scalars().all()
    return [{"id": r.id, "message": r.message, "created_at": r.created_at.isoformat()} for r in rows]
@app.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: int, token: str, db: Session = Depends(get_db)):
    # token from query string ?token=...
    await asyncio.to_thread(get_user_from_token_query, token, db)

    async def event_gen():
        last_id = 0
        # initial burst: send any existing logs
        def fetch():
            return db.execute(
                select(Job, JobLog)
                .join(JobLog, JobLog.job_id == Job.id, isouter=True)
                .where(Job.id == job_id)
                .order_by(JobLog.id.asc())
            ).all()

        # track job status & send new log lines
        # we're polling DB; simple & reliable without extra deps
        while True:
            rows = await asyncio.to_thread(fetch)
            job = None
            for j, log in rows:
                if job is None: job = j
                if log and log.id > last_id:
                    last_id = log.id
                    yield f"data: {log.message}\n\n"
            # also emit periodic progress
            if job:
                yield f"event: progress\ndata: {job.progress}\n\n"
                if job.status in ("completed", "failed"):
                    yield f"event: done\ndata: {job.status}\n\n"
                    break
            await asyncio.sleep(1.0)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
