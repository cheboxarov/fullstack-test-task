import mimetypes
from pathlib import Path
from typing import Protocol

from src.application.errors import StoragePathEscapeError, UploadSizeExceededError


class UploadInput(Protocol):
    filename: str | None
    content_type: str | None

    async def read(self) -> bytes: ...


class PathEscapeError(Exception):
    """Raised when a resolved path escapes the storage directory."""


class LocalFileStorage:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir.resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _safe_resolve(self, stored_name: str) -> Path:
        """Resolve stored_name within storage_dir, rejecting path traversal.

        Raises PathEscapeError if the resolved path escapes storage_dir.
        """
        resolved = (self.storage_dir / stored_name).resolve()
        if not resolved.is_relative_to(self.storage_dir):
            raise PathEscapeError(f"Path '{stored_name}' escapes storage directory")
        return resolved

    async def write_upload(
        self,
        file_id: str,
        upload_file: UploadInput,
        *,
        max_size_bytes: int | None = None,
    ) -> tuple[str, str, int]:
        suffix = Path(upload_file.filename or "").suffix
        stored_name = f"{file_id}{suffix}"
        stored_path = self._safe_resolve(stored_name)

        total_size = 0
        with stored_path.open("wb") as f:
            while chunk := await upload_file.read(8192):
                total_size += len(chunk)
                if max_size_bytes is not None and total_size > max_size_bytes:
                    stored_path.unlink(missing_ok=True)
                    raise UploadSizeExceededError(
                        f"File size exceeds maximum {max_size_bytes} bytes"
                    )
                f.write(chunk)

        mime_type = (
            upload_file.content_type
            or mimetypes.guess_type(stored_name)[0]
            or "application/octet-stream"
        )
        return stored_name, mime_type, total_size

    def resolve_path(self, stored_name: str) -> Path | None:
        """Resolve stored_name to a valid path within storage_dir.

        Returns:
            Path: Resolved path if file exists
            None: If file does not exist (expected case)

        Raises:
            StoragePathEscapeError: If path traversal attempt detected
        """
        try:
            stored_path = self._safe_resolve(stored_name)
        except PathEscapeError:
            raise StoragePathEscapeError(attempted_path=stored_name)
        if not stored_path.exists():
            return None
        return stored_path

    def delete_if_exists(self, stored_name: str) -> None:
        """Delete file if it exists. Idempotent - no error if file not found.

        Raises:
            StoragePathEscapeError: If path traversal attempt detected
        """
        try:
            stored_path = self._safe_resolve(stored_name)
        except PathEscapeError:
            raise StoragePathEscapeError(attempted_path=stored_name)
        if stored_path.exists():
            stored_path.unlink()

    def check_file_exists(self, stored_name: str) -> bool:
        """Check if a file exists in storage.

        Returns:
            True: File exists and path is valid
            False: File does not exist (path is valid)

        Raises:
            StoragePathEscapeError: If path traversal attempt detected
        """
        try:
            stored_path = self._safe_resolve(stored_name)
        except PathEscapeError:
            raise StoragePathEscapeError(attempted_path=stored_name)
        return stored_path.exists()

    def read_text(self, stored_name: str, encoding: str = "utf-8") -> str:
        return self._safe_resolve(stored_name).read_text(encoding=encoding)

    def read_bytes(self, stored_name: str) -> bytes:
        return self._safe_resolve(stored_name).read_bytes()
