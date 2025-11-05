
from app.celery_app import celery
import app.tasks  # ensure tasks are registered
# Run with: celery -A app.celery_app.celery worker -l info
