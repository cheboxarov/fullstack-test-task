"""Celery app factory.

Provides create_celery_app() for creating configured Celery instances.
All actual task logic lives in src.tasks.
"""

from celery import Celery
from sqlalchemy.exc import InterfaceError, OperationalError

from src.bootstrap.settings import Settings

# Retry configuration constants
AUTORETRY_FOR = (OperationalError, InterfaceError)
RETRY_BACKOFF = True
RETRY_BACKOFF_MAX = 300
RETRY_JITTER = True
DEFAULT_MAX_RETRIES = 3


def create_celery_app(settings: Settings) -> Celery:
    """Create and configure a Celery app instance.

    Args:
        settings: Application settings for broker/backend configuration

    Returns:
        Configured Celery instance
    """
    app = Celery("file_tasks")
    app.conf.broker_url = settings.redis_url
    app.conf.result_backend = settings.redis_url
    app.conf.task_default_queue = settings.celery_queue
    app.conf.task_default_exchange = settings.celery_queue
    app.conf.task_default_routing_key = settings.celery_queue
    return app
