"""Entry point for Celery worker tasks.

This is the ONLY module Celery worker needs to know about.
All task definitions, retry configuration, and dispatch logic live here.

Usage:
    celery -A src.tasks worker -l info
"""

import logging
from typing import Callable, TypeVar

from celery import Celery
from sqlalchemy.exc import InterfaceError, OperationalError

from src.application.errors import (
    FileNotFoundError,
    ProcessingError,
    StoredFileMissingError,
)
from src.application.orchestration.pipeline_orchestrator import PipelineOrchestrator
from src.application.use_cases.file_processing import WorkerPipelineStep
from src.bootstrap.container import (
    get_engine,
    get_extract_file_metadata_use_case,
    get_file_repository,
    get_scan_file_for_threats_use_case,
    get_send_file_alert_use_case,
    get_session_maker,
    get_settings,
)
from src.application.worker.event_loop import run_in_worker_loop

# Configure logger with task context support
logger = logging.getLogger(__name__)

# Error classification for proper handling strategy
TRANSIENT_ERRORS = (
    OperationalError,
    InterfaceError,
)  # DB connectivity issues - retryable
BUSINESS_ERRORS = (
    ProcessingError,
    FileNotFoundError,
    StoredFileMissingError,
)  # Terminal errors

T = TypeVar("T")

# Retry configuration for transient DB errors
AUTORETRY_FOR = (OperationalError, InterfaceError)
RETRY_BACKOFF = True
RETRY_BACKOFF_MAX = 300
RETRY_JITTER = True
DEFAULT_MAX_RETRIES = 3

# Lazy-initialized dependencies
db_engine = None
async_session_maker = None
_orchestrator = None


def _ensure_db() -> None:
    """Lazy init DB dependencies."""
    global db_engine, async_session_maker
    if db_engine is None or async_session_maker is None:
        db_engine = get_engine()
        async_session_maker = get_session_maker()


def _get_orchestrator() -> PipelineOrchestrator:
    """Lazy init orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


def try_update_file_status(
    file_id: str, status: str, message: str | None = None, task_name: str | None = None
) -> None:
    """Safely update file processing_status with proper error handling.

    Args:
        file_id: The file ID to update
        status: New processing status (e.g., "failed")
        message: Optional error message for context
        task_name: Optional task name for logging context

    Notes:
        - Logs but doesn't raise if DB unavailable (transient error)
        - Creates alert for the failure if possible
        - Safe to call during error handling when state is uncertain
    """
    # Build log extra context
    log_extra = {"file_id": file_id}
    if task_name:
        log_extra["task_name"] = task_name

    try:
        _ensure_db()
        repo = get_file_repository()

        async def _update() -> None:
            async with repo.session() as session:
                file_record = await repo.get_by_id(file_id)
                if file_record:
                    file_record.processing_status = status
                    if message:
                        file_record.processing_message = message[
                            :500
                        ]  # Truncate long messages
                    await session.commit()
                    logger.info(
                        f"Updated file {file_id} status to '{status}'", extra=log_extra
                    )
                else:
                    logger.warning(
                        f"File {file_id} not found for status update", extra=log_extra
                    )

        run_in_worker_loop(_update())
    except TRANSIENT_ERRORS as e:
        # DB unavailable - log but don't fail, retry will handle this
        logger.warning(
            f"DB unavailable when updating file {file_id} status: {e}",
            extra={**log_extra, "error_type": type(e).__name__},
        )
    except Exception as e:
        # Unexpected error during status update - log but don't suppress original error
        logger.error(
            f"Failed to update file {file_id} status to '{status}': {e}",
            extra={**log_extra, "error_type": type(e).__name__},
        )


def execute_task_with_handling(
    task_name: str, file_id: str, execute_fn: Callable[[], T]
) -> T:
    """Execute task logic with structured error handling and logging.

    Args:
        task_name: Name of the task for logging context
        file_id: File ID being processed for context
        execute_fn: Callable that performs the actual task work

    Returns:
        Result from execute_fn

    Raises:
        Re-raises all exceptions after proper logging and state management.
        Celery will retry TRANSIENT_ERRORS based on autoretry_for.
    """
    try:
        logger.info(f"Starting {task_name} for file_id={file_id}")
        result = execute_fn()
        logger.info(f"Completed {task_name} for file_id={file_id}")
        return result
    except TRANSIENT_ERRORS as e:
        # Transient errors (DB issues) - log with context and re-raise for Celery retry
        logger.warning(
            f"Transient error in {task_name} for file_id={file_id}: {type(e).__name__}: {e}"
        )
        raise  # Celery will retry based on autoretry_for
    except BUSINESS_ERRORS as e:
        # Business errors (file missing, processing failed) - terminal, no retry
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(
            f"Business error in {task_name} for file_id={file_id}: {error_msg}",
            extra={
                "file_id": file_id,
                "task_name": task_name,
                "error_code": getattr(e, "code", "unknown"),
            },
        )
        # Try to set file to failed state (best effort)
        try_update_file_status(file_id, "failed", str(e)[:200], task_name=task_name)
        raise  # Don't retry business errors - they won't succeed on retry
    except Exception as e:
        # Unexpected error - log full context with stack trace
        logger.exception(
            f"Unexpected error in {task_name} for file_id={file_id}: {type(e).__name__}: {e}",
            extra={
                "file_id": file_id,
                "task_name": task_name,
                "error_type": type(e).__name__,
            },
        )
        # Try to set file to failed state
        try_update_file_status(file_id, "failed", "internal_error", task_name=task_name)
        raise  # Re-raise - Celery will mark as failed


# Create Celery app
settings = get_settings()
celery_app = Celery("file_tasks")
celery_app.conf.broker_url = settings.redis_url
celery_app.conf.result_backend = settings.redis_url
celery_app.conf.task_default_queue = settings.celery_queue
celery_app.conf.task_default_exchange = settings.celery_queue
celery_app.conf.task_default_routing_key = settings.celery_queue


@celery_app.task(
    autoretry_for=AUTORETRY_FOR,
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    max_retries=DEFAULT_MAX_RETRIES,
    retry_jitter=RETRY_JITTER,
    name="scan_file_for_threats",
)
def scan_file_for_threats(file_id: str) -> None:
    """Scan file for threats and dispatch next step.

    Args:
        file_id: ID of the file to scan

    Error handling:
        - Transient errors (DB issues): Celery will retry
        - Business errors (file missing): Terminal, sets file to failed state
        - Unexpected errors: Terminal, full logging, sets file to failed state
    """

    def _execute():
        _ensure_db()
        use_case = get_scan_file_for_threats_use_case()
        result = run_in_worker_loop(use_case.execute(file_id))
        next_step = _get_orchestrator().determine_next_step(
            WorkerPipelineStep(task_name="scan_file_for_threats", file_id=file_id),
            result,
            None,
        )
        if next_step:
            celery_app.send_task(next_step.task_name, args=[next_step.file_id])

    execute_task_with_handling("scan_file_for_threats", file_id, _execute)


@celery_app.task(
    autoretry_for=AUTORETRY_FOR,
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    max_retries=DEFAULT_MAX_RETRIES,
    retry_jitter=RETRY_JITTER,
    name="extract_file_metadata",
)
def extract_file_metadata(file_id: str) -> None:
    """Extract file metadata and dispatch next step.

    Args:
        file_id: ID of the file to process

    Error handling:
        - Transient errors (DB issues): Celery will retry
        - Business errors (file missing, storage issues): Terminal, sets file to failed state
        - Unexpected errors: Terminal, full logging, sets file to failed state
    """

    def _execute():
        _ensure_db()
        use_case = get_extract_file_metadata_use_case()
        result = run_in_worker_loop(use_case.execute(file_id))
        next_step = _get_orchestrator().determine_next_step(
            WorkerPipelineStep(task_name="extract_file_metadata", file_id=file_id),
            result,
            None,
        )
        if next_step:
            celery_app.send_task(next_step.task_name, args=[next_step.file_id])

    execute_task_with_handling("extract_file_metadata", file_id, _execute)


@celery_app.task(
    autoretry_for=AUTORETRY_FOR,
    retry_backoff=RETRY_BACKOFF,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    max_retries=DEFAULT_MAX_RETRIES,
    retry_jitter=RETRY_JITTER,
    name="send_file_alert",
)
def send_file_alert(file_id: str) -> None:
    """Send file alert - terminal task.

    Args:
        file_id: ID of the file to send alert for

    Error handling:
        - Transient errors (DB issues): Celery will retry
        - Business errors (file missing, alert creation failed): Terminal, sets file to failed state
        - Unexpected errors: Terminal, full logging, sets file to failed state

    Note:
        This is a terminal task - no next step is dispatched.
    """

    def _execute():
        _ensure_db()
        use_case = get_send_file_alert_use_case()
        run_in_worker_loop(use_case.execute(file_id))

    execute_task_with_handling("send_file_alert", file_id, _execute)


__all__ = [
    "celery_app",
    "scan_file_for_threats",
    "extract_file_metadata",
    "send_file_alert",
]
