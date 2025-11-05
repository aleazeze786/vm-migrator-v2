import logging
import sys
from typing import Dict

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOGGERS: Dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger configured to emit structured messages to stdout.
    Ensures we do not attach multiple handlers when imported by
    both the API process and the worker.
    """
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
    logger.propagate = False
    _LOGGERS[name] = logger
    return logger


def record_system_event(level: str, component: str, message: str) -> None:
    """
    Persist a high-level event for display in the UI while also logging it.
    Failures here should never bubble up to callers.
    """
    logger = get_logger("vm_migrator.events")
    logger.log(getattr(logging, level.upper(), logging.INFO), "%s: %s", component, message)
    try:
        from .database import SessionLocal  # local import to avoid circular deps
        from .models import SystemLog

        db = SessionLocal()
        try:
            db.add(SystemLog(level=level.upper(), component=component, message=message))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to persist system event component=%s message=%s", component, message)
