import asyncio
from datetime import timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.exc import UnknownHashError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, API_TITLE, SECRET_KEY
from .database import Base, engine, get_db
from .integrations.proxmox import ProxmoxError, fetch_nodes
from .integrations.vcenter import VCenterError, fetch_inventory
from .logging_utils import get_logger, record_system_event
from .models import (
    Job,
    JobLog,
    Provider,
    ProviderType,
    ProxmoxNode,
    User,
    VCenterDatacenter,
    VCenterHost,
    VirtualMachine,
    SystemLog,
)
from .schemas import (
    BatchJobCreate,
    JobCreate,
    JobOut,
    ProviderCreate,
    ProviderOut,
    Token,
    UserOut,
    VCenterDatacenterOut,
    VCenterHostOut,
    VirtualMachineOut,
    ProxmoxNodeOut,
    SystemLogOut,
)
from .security import create_access_token, get_password_hash, verify_password
from .tasks import execute_migration_job

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
logger = get_logger("vm_migrator.api")

app = FastAPI(title=API_TITLE)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(bind=engine)

def seed_admin(db: Session):
    existing = db.query(User).filter(User.username == "admin").first()
    if not existing:
        db.add(User(username="admin", hashed_password=get_password_hash("admin"), role="admin"))
        db.commit()
        logger.info("Seeded default admin user")
        record_system_event("INFO", "auth", "Seeded default admin user")
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


def _get_provider_or_404(db: Session, pid: int) -> Provider:
    provider = db.get(Provider, pid)
    if not provider:
        logger.error("Provider not found id=%s", pid)
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


def _ensure_credentials(provider: Provider) -> None:
    if not provider.username or not provider.secret:
        logger.error(
            "Provider missing credentials id=%s type=%s", provider.id, provider.type.value
        )
        raise HTTPException(
            status_code=400,
            detail="Provider is missing username or secret. Update credentials before syncing.",
        )


def _sync_vcenter_inventory(db: Session, provider: Provider) -> dict:
    inventory = fetch_inventory(
        api_url=provider.api_url,
        username=provider.username or "",
        password=provider.secret or "",
        verify_ssl=provider.verify_ssl,
    )

    db.query(VirtualMachine).filter(
        VirtualMachine.provider_id == provider.id
    ).delete(synchronize_session=False)
    db.query(VCenterHost).filter(
        VCenterHost.provider_id == provider.id
    ).delete(synchronize_session=False)
    db.query(VCenterDatacenter).filter(
        VCenterDatacenter.provider_id == provider.id
    ).delete(synchronize_session=False)
    db.commit()

    dc_map = {}
    for dc in inventory.datacenters:
        row = VCenterDatacenter(
            provider_id=provider.id,
            name=dc.name,
            moid=dc.moid,
        )
        db.add(row)
        db.flush()
        dc_map[dc.moid] = row.id

    host_map = {}
    for host in inventory.hosts:
        row = VCenterHost(
            provider_id=provider.id,
            datacenter_id=dc_map.get(host.datacenter_moid),
            name=host.name,
            moid=host.moid,
            cpu_cores=host.cpu_cores,
            memory_bytes=host.memory_bytes,
            product=host.product,
            version=host.version,
        )
        db.add(row)
        db.flush()
        host_map[host.moid] = row.id

    for vm in inventory.virtual_machines:
        db.add(
            VirtualMachine(
                provider_id=provider.id,
                vcenter_host_id=host_map.get(vm.host_moid),
                source_identifier=vm.moid,
                name=vm.name,
                power_state=vm.power_state,
                cpu_count=vm.cpu_count,
                memory_bytes=vm.memory_bytes,
                storage_gb=vm.storage_gb,
                os=vm.os,
            )
        )

    db.commit()
    return {
        "datacenters": len(inventory.datacenters),
        "hosts": len(inventory.hosts),
        "virtual_machines": len(inventory.virtual_machines),
    }


def _sync_proxmox_nodes(db: Session, provider: Provider) -> dict:
    nodes = fetch_nodes(
        api_url=provider.api_url,
        username=provider.username or "",
        secret=provider.secret or "",
        verify_ssl=provider.verify_ssl,
    )

    db.query(ProxmoxNode).filter(
        ProxmoxNode.provider_id == provider.id
    ).delete(synchronize_session=False)

    for node in nodes:
        db.add(
            ProxmoxNode(
                provider_id=provider.id,
                name=node.name,
                status=node.status,
                cpu_usage=node.cpu_usage,
                memory_usage=node.memory_usage,
            )
        )

    db.commit()
    return {"nodes": len(nodes)}


# ---------- Providers ----------
@app.post("/api/providers", response_model=ProviderOut)
def create_provider(payload: ProviderCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    provider_type = ProviderType(payload.type)

    if provider_type in (ProviderType.vcenter, ProviderType.proxmox) and (
        not payload.api_url or not payload.username or not payload.secret
    ):
        record_system_event(
            "ERROR",
            "provider",
            "Cannot add provider without API URL, username, and secret",
        )
        raise HTTPException(
            status_code=400,
            detail="API URL, username, and password/token are required",
        )

    if provider_type == ProviderType.vcenter:
        try:
            fetch_inventory(
                api_url=payload.api_url,
                username=payload.username or "",
                password=payload.secret or "",
                verify_ssl=payload.verify_ssl,
            )
        except VCenterError as exc:
            logger.error("Provider validation failed type=vcenter error=%s", exc)
            record_system_event("ERROR", "provider", f"Failed to validate vCenter credentials: {exc}")
            raise HTTPException(status_code=400, detail=f"Unable to connect to vCenter: {exc}")
    elif provider_type == ProviderType.proxmox:
        try:
            fetch_nodes(
                api_url=payload.api_url,
                username=payload.username or "",
                secret=payload.secret or "",
                verify_ssl=payload.verify_ssl,
            )
        except ProxmoxError as exc:
            logger.error("Provider validation failed type=proxmox error=%s", exc)
            record_system_event("ERROR", "provider", f"Failed to validate Proxmox credentials: {exc}")
            raise HTTPException(status_code=400, detail=f"Unable to connect to Proxmox: {exc}")

    p = Provider(name=payload.name, type=provider_type, api_url=payload.api_url,
                 username=payload.username, secret=payload.secret, verify_ssl=payload.verify_ssl)
    db.add(p); db.commit(); db.refresh(p)
    logger.info("Provider created id=%s type=%s name=%s", p.id, p.type.value, p.name)
    record_system_event("INFO", "provider", f"Added provider '{p.name}' ({p.type.value})")
    return p

@app.get("/api/providers", response_model=List[ProviderOut])
def list_providers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Provider).order_by(Provider.id.desc()).all()

@app.delete("/api/providers/{pid}")
def delete_provider(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = _get_provider_or_404(db, pid)
    db.delete(p); db.commit()
    logger.info("Provider deleted id=%s name=%s", p.id, p.name)
    record_system_event("INFO", "provider", f"Deleted provider '{p.name}'")
    return {"ok": True}

@app.post("/api/providers/{pid}/sync")
def sync_provider(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    provider = _get_provider_or_404(db, pid)
    _ensure_credentials(provider)
    try:
        if provider.type == ProviderType.vcenter:
            result = _sync_vcenter_inventory(db, provider)
        elif provider.type == ProviderType.proxmox:
            result = _sync_proxmox_nodes(db, provider)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider type")
    except (VCenterError, ProxmoxError) as exc:
        logger.error(
            "Provider sync failed id=%s type=%s error=%s",
            provider.id,
            provider.type.value,
            exc,
        )
        record_system_event(
            "ERROR",
            "provider",
            f"Sync failed for provider '{provider.name}' ({provider.type.value}): {exc}",
        )
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info(
        "Provider sync complete id=%s type=%s details=%s",
        provider.id,
        provider.type.value,
        result,
    )
    record_system_event(
        "INFO",
        "provider",
        f"Sync completed for provider '{provider.name}' ({provider.type.value})",
    )
    return {"ok": True, **result}

# ---------- Inventory ----------
@app.get("/api/providers/{pid}/datacenters", response_model=List[VCenterDatacenterOut])
def provider_datacenters(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    provider = _get_provider_or_404(db, pid)
    if provider.type != ProviderType.vcenter:
        raise HTTPException(status_code=400, detail="Provider does not support datacenters")
    rows = db.query(VCenterDatacenter).filter(
        VCenterDatacenter.provider_id == provider.id
    ).order_by(VCenterDatacenter.name.asc()).all()
    return rows


@app.get("/api/providers/{pid}/hosts", response_model=List[VCenterHostOut])
def provider_hosts(
    pid: int,
    datacenter_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    provider = _get_provider_or_404(db, pid)
    if provider.type != ProviderType.vcenter:
        logger.warning(
            "Host inventory requested for non-vCenter provider id=%s type=%s",
            provider.id,
            provider.type.value,
        )
        raise HTTPException(status_code=400, detail="Provider does not support hosts")

    query = db.query(VCenterHost).filter(VCenterHost.provider_id == provider.id)
    if datacenter_id:
        query = query.filter(VCenterHost.datacenter_id == datacenter_id)
    return query.order_by(VCenterHost.name.asc()).all()


@app.get("/api/providers/{pid}/nodes", response_model=List[ProxmoxNodeOut])
def provider_nodes(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    provider = _get_provider_or_404(db, pid)
    if provider.type != ProviderType.proxmox:
        logger.warning(
            "Node inventory requested for non-Proxmox provider id=%s type=%s",
            provider.id,
            provider.type.value,
        )
        raise HTTPException(status_code=400, detail="Provider does not support nodes")
    return (
        db.query(ProxmoxNode)
        .filter(ProxmoxNode.provider_id == provider.id)
        .order_by(ProxmoxNode.name.asc())
        .all()
    )


@app.get("/api/vms", response_model=List[VirtualMachineOut])
def list_vms(
    provider_id: Optional[int] = Query(None),
    host_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(VirtualMachine)
    if provider_id:
        query = query.filter(VirtualMachine.provider_id == provider_id)
    if host_id:
        query = query.filter(VirtualMachine.vcenter_host_id == host_id)
    return query.order_by(VirtualMachine.name.asc()).all()

# ---------- Jobs ----------
@app.post("/api/jobs", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    source_provider = _get_provider_or_404(db, payload.source_provider_id)
    destination_provider = _get_provider_or_404(db, payload.destination_provider_id)

    vm = db.get(VirtualMachine, payload.source_vm_id)
    if not vm:
        logger.error(
            "Job creation failed: VM missing vm_id=%s source_provider=%s",
            payload.source_vm_id,
            source_provider.id,
        )
        record_system_event(
            "ERROR",
            "job",
            f"Failed to queue job: source VM {payload.source_vm_id} not found",
        )
        raise HTTPException(status_code=404, detail="Source VM not found")
    if vm.provider_id != source_provider.id:
        logger.error(
            "Job creation failed: VM provider mismatch vm_id=%s vm_provider=%s expected=%s",
            vm.id,
            vm.provider_id,
            source_provider.id,
        )
        record_system_event(
            "ERROR",
            "job",
            f"Failed to queue job for VM '{vm.name}': provider mismatch",
        )
        raise HTTPException(
            status_code=400,
            detail="Virtual machine does not belong to the selected source provider",
        )
    if source_provider.type != ProviderType.vcenter:
        logger.error(
            "Job creation failed: source provider not vCenter id=%s type=%s",
            source_provider.id,
            source_provider.type.value,
        )
        record_system_event(
            "ERROR",
            "job",
            "Failed to queue job: source provider must be VMware vCenter",
        )
        raise HTTPException(status_code=400, detail="Source provider must be vCenter")
    if destination_provider.type != ProviderType.proxmox:
        logger.error(
            "Job creation failed: destination provider not Proxmox id=%s type=%s",
            destination_provider.id,
            destination_provider.type.value,
        )
        record_system_event(
            "ERROR",
            "job",
            "Failed to queue job: destination provider must be Proxmox VE",
        )
        raise HTTPException(
            status_code=400, detail="Destination provider must be Proxmox VE"
        )

    job = Job(
        vm_name=vm.name,
        status="queued",
        progress=0,
        source_provider_id=source_provider.id,
        destination_provider_id=destination_provider.id,
        source_vm_id=vm.id,
        target_node=payload.target_node,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    execute_migration_job.apply_async(args=[job.id])
    logger.info(
        "Job queued id=%s vm=%s source_provider=%s destination_provider=%s target_node=%s",
        job.id,
        job.vm_name,
        job.source_provider_id,
        job.destination_provider_id,
        job.target_node,
    )
    record_system_event(
        "INFO",
        "job",
        f"Queued migration job #{job.id} for VM '{job.vm_name}'",
    )
    return job

@app.post("/api/jobs/batch", response_model=List[JobOut])
def create_batch(payload: BatchJobCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    source_provider = _get_provider_or_404(db, payload.source_provider_id)
    destination_provider = _get_provider_or_404(db, payload.destination_provider_id)
    if source_provider.type != ProviderType.vcenter or destination_provider.type != ProviderType.proxmox:
        logger.error(
            "Batch job creation failed: source_type=%s destination_type=%s",
            source_provider.type.value,
            destination_provider.type.value,
        )
        record_system_event(
            "ERROR",
            "job",
            "Failed to queue batch jobs: invalid provider types",
        )
        raise HTTPException(
            status_code=400,
            detail="Batch jobs require vCenter source and Proxmox destination providers",
        )

    vms = (
        db.query(VirtualMachine)
        .filter(VirtualMachine.id.in_(payload.source_vm_ids))
        .all()
    )
    vm_map = {vm.id: vm for vm in vms}

    missing = [vm_id for vm_id in payload.source_vm_ids if vm_id not in vm_map]
    if missing:
        logger.error(
            "Batch job creation failed: missing VMs %s", ",".join(map(str, missing))
        )
        record_system_event(
            "ERROR",
            "job",
            f"Failed to queue batch jobs: missing VMs {', '.join(map(str, missing))}",
        )
        raise HTTPException(
            status_code=404,
            detail=f"Virtual machines not found: {', '.join(map(str, missing))}",
        )

    out = []
    for vm_id in payload.source_vm_ids:
        vm = vm_map[vm_id]
        if vm.provider_id != source_provider.id:
            raise HTTPException(
                status_code=400,
                detail=f"VM '{vm.name}' does not belong to source provider",
            )
        job = Job(
            vm_name=vm.name,
            status="queued",
            progress=0,
            source_provider_id=source_provider.id,
            destination_provider_id=destination_provider.id,
            source_vm_id=vm.id,
            target_node=payload.target_node,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        execute_migration_job.apply_async(args=[job.id])
        logger.info(
            "Batch job queued id=%s vm=%s source_provider=%s destination_provider=%s target_node=%s",
            job.id,
            job.vm_name,
            job.source_provider_id,
            job.destination_provider_id,
            job.target_node,
        )
        record_system_event(
            "INFO",
            "job",
            f"Queued migration job #{job.id} for VM '{job.vm_name}'",
        )
        out.append(job)
    return out

@app.get("/api/jobs", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Job).order_by(Job.id.desc()).all()

@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "Job not found")
    return job
def get_user_from_token_query(token: str, db: Session) -> User:
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


@app.get("/api/logs/system", response_model=List[SystemLogOut])
def list_system_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(SystemLog)
        .order_by(SystemLog.id.desc())
        .limit(limit)
        .all()
    )
    return rows
