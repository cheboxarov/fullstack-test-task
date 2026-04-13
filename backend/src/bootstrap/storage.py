from pathlib import Path

from src.bootstrap.settings import Settings


def get_storage_dir(settings: Settings) -> Path:
    storage_dir = settings.storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir
