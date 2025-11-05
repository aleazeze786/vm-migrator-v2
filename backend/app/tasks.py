import time
from sqlalchemy.orm import Session
from .celery_app import celery
from .database import SessionLocal
from .models import Job, JobLog

def _log(db: Session, job_id: int, msg: str):
    db.add(JobLog(job_id=job_id, message=msg))
    db.commit()

@celery.task(name="tasks.fake_migrate_vm", bind=True)
def fake_migrate_vm(self, job_id: int, vm_name: str):
    db: Session = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return {"ok": False, "error": f"Job {job_id} not found"}
        job.status = "running"; job.progress = 0; db.commit()
        _log(db, job_id, f"Queued vm={vm_name}")
        _log(db, job_id, "Starting…")

        phases = [("snapshot", 20), ("convert", 60), ("upload", 85), ("finalize", 100)]
        for phase, target in phases:
            _log(db, job_id, f"Phase: {phase}")
            while job.progress < target:
                time.sleep(0.4)
                job.progress = min(job.progress + 5, target)
                db.commit()
                self.update_state(state="PROGRESS", meta={"progress": job.progress, "phase": phase})

        job.status = "completed"; db.commit()
        _log(db, job_id, "Completed successfully.")
        return {"ok": True, "job_id": job_id, "vm_name": vm_name}
    except Exception as e:
        try:
            job = db.get(Job, job_id)
            if job:
                job.status = "failed"; db.commit()
                _log(db, job_id, f"Failed: {type(e).__name__}: {e}")
        except Exception:
            pass
        raise
    finally:
        db.close()
