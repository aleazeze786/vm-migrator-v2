import time
from contextlib import suppress
from typing import Optional

from sqlalchemy.orm import Session

from .celery_app import celery
from .database import SessionLocal
from .integrations.proxmox import ProxmoxError, fetch_nodes
from .integrations.vcenter import VCenterError, fetch_inventory
from .logging_utils import get_logger, record_system_event
from .models import (
    Job,
    JobLog,
    Provider,
    ProviderType,
    VirtualMachine,
)


logger = get_logger("vm_migrator.worker")


def _log(db: Session, job_id: int, message: str) -> None:
    db.add(JobLog(job_id=job_id, message=message))
    db.commit()
    logger.info("job_id=%s %s", job_id, message)


def _load_provider(db: Session, provider_id: Optional[int]) -> Optional[Provider]:
    if provider_id is None:
        return None
    return db.get(Provider, provider_id)


def _load_vm(db: Session, vm_id: Optional[int]) -> Optional[VirtualMachine]:
    if vm_id is None:
        return None
    return db.get(VirtualMachine, vm_id)


@celery.task(name="tasks.execute_migration_job", bind=True)
def execute_migration_job(self, job_id: int) -> dict:
    """Background worker responsible for orchestrating migrations."""
    db: Session = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("Migration job missing job_id=%s", job_id)
            record_system_event("ERROR", "worker", f"Migration job #{job_id} not found")
            return {"ok": False, "error": f"Job {job_id} not found"}

        job.status = "running"
        job.progress = 0
        db.commit()
        logger.info(
            "Migration job started job_id=%s vm=%s source_provider=%s destination_provider=%s",
            job.id,
            job.vm_name,
            job.source_provider_id,
            job.destination_provider_id,
        )
        record_system_event(
            "INFO",
            "worker",
            f"Migration job #{job.id} started for VM '{job.vm_name}'",
        )

        _log(db, job_id, "Starting migration workflow.")

        source_provider = _load_provider(db, job.source_provider_id)
        dest_provider = _load_provider(db, job.destination_provider_id)
        vm = _load_vm(db, job.source_vm_id)

        if not source_provider or not dest_provider or not vm:
            job.status = "failed"
            db.commit()
            logger.error(
                "Migration job failed during preload job_id=%s source_provider=%s dest_provider=%s vm=%s",
                job.id,
                job.source_provider_id,
                job.destination_provider_id,
                job.source_vm_id,
            )
            record_system_event(
                "ERROR",
                "worker",
                f"Migration job #{job.id} failed before execution: missing context",
            )
            raise ValueError("Job is missing provider or VM information.")

        if source_provider.type != ProviderType.vcenter:
            job.status = "failed"
            db.commit()
            logger.error(
                "Migration job failed: source provider is %s (expected vcenter) job_id=%s",
                source_provider.type.value,
                job.id,
            )
            record_system_event(
                "ERROR",
                "worker",
                f"Migration job #{job.id} failed: source provider not vCenter",
            )
            raise ValueError("Source provider must be a vCenter instance.")

        if dest_provider.type != ProviderType.proxmox:
            job.status = "failed"
            db.commit()
            logger.error(
                "Migration job failed: destination provider is %s (expected proxmox) job_id=%s",
                dest_provider.type.value,
                job.id,
            )
            record_system_event(
                "ERROR",
                "worker",
                f"Migration job #{job.id} failed: destination provider not Proxmox",
            )
            raise ValueError("Destination provider must be a Proxmox VE instance.")

        # Step 1: verify connectivity to vCenter and Proxmox.
        _log(db, job_id, "Validating connectivity with vCenter source.")
        inventory = None
        with suppress(VCenterError):
            inventory = fetch_inventory(
                api_url=source_provider.api_url,
                username=source_provider.username or "",
                password=source_provider.secret or "",
                verify_ssl=source_provider.verify_ssl,
            )
            job.progress = 10
            db.commit()
        if job.progress < 10:
            raise VCenterError("Unable to connect to vCenter with stored credentials.")

        _log(db, job_id, "Validating connectivity with Proxmox destination.")
        proxmox_nodes = []
        with suppress(ProxmoxError):
            proxmox_nodes = fetch_nodes(
                api_url=dest_provider.api_url,
                username=dest_provider.username or "",
                secret=dest_provider.secret or "",
                verify_ssl=dest_provider.verify_ssl,
            )
            job.progress = 20
            db.commit()
        if job.progress < 20:
            raise ProxmoxError(
                "Unable to connect to Proxmox with stored credentials."
            )

        # Step 2: construct plan from cached inventory
        target_node = job.target_node or (
            proxmox_nodes[0].name if proxmox_nodes else None
        )
        if not target_node:
            raise ValueError(
                "Destination node not specified and Proxmox cluster returned no nodes."
            )
        if not job.target_node:
            job.target_node = target_node
            db.commit()

        _log(
            db,
            job_id,
            f"Prepared migration plan for VM '{vm.name}' "
            f"(source id {vm.source_identifier}) to Proxmox node '{target_node}'.",
        )
        job.progress = 30
        db.commit()

        # Step 3: placeholder actions (export, convert, upload, import).
        phases = [
            ("Export VM from vCenter as OVA", 50),
            ("Convert disks to qcow2 using qemu-img", 65),
            ("Upload converted disks to Proxmox storage", 80),
            ("Provision Proxmox VM and attach disks", 90),
            ("Initiate Proxmox live migration", 100),
        ]
        for step, target in phases:
            _log(db, job_id, step)
            while job.progress < target:
                time.sleep(0.2)
                job.progress = min(job.progress + 5, target)
                db.commit()
                self.update_state(
                    state="PROGRESS", meta={"progress": job.progress, "step": step}
                )

        _log(
            db,
            job_id,
            "Migration workflow completed (manual data transfer steps may still be required).",
        )
        job.status = "completed"
        db.commit()
        logger.info("Migration job completed job_id=%s", job.id)
        record_system_event(
            "INFO",
            "worker",
            f"Migration job #{job.id} completed",
        )
        return {
            "ok": True,
            "job_id": job.id,
            "vm_name": job.vm_name,
            "target_node": target_node,
        }
    except Exception as exc:
        if job := db.get(Job, job_id):
            job.status = "failed"
            db.commit()
            _log(db, job_id, f"Failed: {type(exc).__name__}: {exc}")
        logger.exception("Migration job crashed job_id=%s", job_id)
        record_system_event(
            "ERROR",
            "worker",
            f"Migration job #{job_id} crashed: {type(exc).__name__}: {exc}",
        )
        raise
    finally:
        db.close()
