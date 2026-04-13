import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_STORAGE_DIR = BASE_DIR / "storage" / "files"


@dataclass(frozen=True, slots=True)
class Settings:
    postgres_user: str | None
    postgres_password: str | None
    postgres_host: str | None
    postgres_port: str | None
    postgres_db: str | None
    storage_dir: Path
    redis_url: str
    celery_broker_url: str
    celery_queue: str
    max_upload_size_bytes: int
    upload_rate_limit_per_minute: int
    retry_max_attempts: int
    retry_backoff_base_seconds: int


def load_settings() -> Settings:
    redis_url = os.environ.get("REDIS_URL") or os.environ.get(
        "CELERY_BROKER_URL", "redis://backend-redis:6379/0"
    )
    return Settings(
        postgres_user=os.environ.get("POSTGRES_USER"),
        postgres_password=os.environ.get("POSTGRES_PASSWORD"),
        postgres_host=os.environ.get("POSTGRES_HOST"),
        postgres_port=os.environ.get("PGPORT"),
        postgres_db=os.environ.get("POSTGRES_DB"),
        storage_dir=Path(os.environ.get("STORAGE_DIR", DEFAULT_STORAGE_DIR)),
        redis_url=redis_url,
        celery_broker_url=os.environ.get("CELERY_BROKER_URL", redis_url),
        celery_queue=os.environ.get("CELERY_QUEUE", "file-processing-mvp"),
        max_upload_size_bytes=int(
            os.environ.get("MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024)
        ),
        upload_rate_limit_per_minute=int(
            os.environ.get("UPLOAD_RATE_LIMIT_PER_MINUTE", 10)
        ),
        retry_max_attempts=int(os.environ.get("RETRY_MAX_ATTEMPTS", "3")),
        retry_backoff_base_seconds=int(
            os.environ.get("RETRY_BACKOFF_BASE_SECONDS", "5")
        ),
    )
