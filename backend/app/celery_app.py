
from celery import Celery
from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery = Celery("vm_migrator",
                broker=CELERY_BROKER_URL,
                backend=CELERY_RESULT_BACKEND)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
