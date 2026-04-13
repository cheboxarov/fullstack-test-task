from typing import Optional


class ApplicationError(Exception):
    """Base application error with rich metadata for API responses and logging.

    Attributes:
        code: Stable error code for client handling (e.g., "file_not_found")
        message: User-facing error message in Russian
        http_status: HTTP status code for the response
        retryable: Whether the client can retry the request
        details: Additional context for the client (e.g., file_id)
        internal_detail: Internal details for logging only (not sent to client)
    """

    code: str = "application_error"
    message: str = "Внутренняя ошибка сервера"
    http_status: int = 500
    retryable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[dict] = None,
        internal_detail: Optional[str] = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        self.internal_detail = internal_detail
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response serialization."""
        result: dict = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            result["details"] = self.details
        return result


class FileNotFoundError(ApplicationError):
    """File not found in database."""

    code = "file_not_found"
    message = "Файл не найден"
    http_status = 404
    retryable = False

    def __init__(self, file_id: Optional[str] = None, **kwargs) -> None:
        details = {"file_id": file_id} if file_id else None
        super().__init__(details=details, **kwargs)


class StoredFileMissingError(ApplicationError):
    """File record exists but physical file is missing from storage."""

    code = "stored_file_missing"
    message = "Файл отсутствует в хранилище"
    http_status = 404
    retryable = False

    def __init__(
        self, file_id: Optional[str] = None, path: Optional[str] = None, **kwargs
    ) -> None:
        details: dict = {}
        if file_id:
            details["file_id"] = file_id
        if path:
            details["path"] = path
        super().__init__(details=details if details else None, **kwargs)


class EmptyUploadError(ApplicationError):
    """Uploaded file has zero bytes."""

    code = "empty_upload"
    message = "Загруженный файл пуст"
    http_status = 400
    retryable = False


class UploadSizeExceededError(ApplicationError):
    """Uploaded file exceeds maximum allowed size."""

    code = "upload_size_exceeded"
    message = "Размер файла превышает допустимый лимит"
    http_status = 413
    retryable = False

    def __init__(
        self,
        max_size: Optional[int] = None,
        actual_size: Optional[int] = None,
        **kwargs,
    ) -> None:
        details: dict = {}
        if max_size is not None:
            details["max_size"] = max_size
        if actual_size is not None:
            details["actual_size"] = actual_size
        super().__init__(details=details if details else None, **kwargs)


class ProcessingError(ApplicationError):
    """Background processing error (e.g., Celery worker failure)."""

    code = "processing_error"
    message = "Ошибка обработки файла"
    http_status = 500
    retryable = False


class StoragePathEscapeError(ApplicationError):
    """Path traversal attempt detected (e.g., ../../../etc/passwd)."""

    code = "storage_path_escape"
    message = "Недопустимый путь к файлу"
    http_status = 400
    retryable = False

    def __init__(self, attempted_path: Optional[str] = None, **kwargs) -> None:
        details = {"attempted_path": attempted_path} if attempted_path else None
        super().__init__(details=details, **kwargs)


class ValidationError(ApplicationError):
    """Input validation error with field-level details."""

    code = "validation_error"
    message = "Ошибка валидации"
    http_status = 422
    retryable = False

    def __init__(self, fields: Optional[dict[str, list[str]]] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.fields = fields or {}

    def to_dict(self) -> dict:
        """Convert to dictionary including field-level errors."""
        result = super().to_dict()
        if self.fields:
            result["fields"] = self.fields
        return result
