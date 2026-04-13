from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from src.application.errors import (
    EmptyUploadError,
    FileNotFoundError,
    StoredFileMissingError,
    UploadSizeExceededError,
)
from src.application.ports import FileRepository, StorageGateway
from src.domain.models import FileRecord


class UploadInput(Protocol):
    filename: str | None
    content_type: str | None

    async def read(self) -> bytes: ...


class CreateFileUseCase:
    def __init__(
        self,
        file_repository: FileRepository,
        storage_gateway: StorageGateway,
        max_upload_size_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self.file_repository = file_repository
        self.storage_gateway = storage_gateway
        self.max_upload_size_bytes = max_upload_size_bytes

    async def execute(self, *, title: str, upload_file: UploadInput) -> FileRecord:
        # Pre-check file size from Content-Length if available (early rejection).
        # The streaming guard in write_upload enforces the limit regardless
        # of whether Content-Length is present (CC-008).
        if (
            upload_file.size is not None
            and upload_file.size > self.max_upload_size_bytes
        ):
            raise UploadSizeExceededError(
                f"File size {upload_file.size} exceeds maximum {self.max_upload_size_bytes}"
            )
        file_id = str(uuid4())
        stored_name, mime_type, size = await self.storage_gateway.write_upload(
            file_id, upload_file, max_size_bytes=self.max_upload_size_bytes
        )
        if size == 0:
            self.storage_gateway.delete_if_exists(stored_name)
            raise EmptyUploadError("File is empty")

        now = datetime.now(timezone.utc)
        file_record = FileRecord(
            id=file_id,
            title=title,
            original_name=upload_file.filename or stored_name,
            stored_name=stored_name,
            mime_type=mime_type,
            size=size,
            processing_status="uploaded",
            scan_status=None,
            scan_details=None,
            metadata_json=None,
            requires_attention=False,
            created_at=now,
            updated_at=now,
        )
        return await self.file_repository.insert_file(file_record)


class UpdateFileUseCase:
    def __init__(self, file_repository: FileRepository) -> None:
        self.file_repository = file_repository

    async def execute(self, *, file_id: str, title: str) -> FileRecord:
        file_record = await self.file_repository.update_title(file_id, title)
        if file_record is None:
            raise FileNotFoundError("File not found")
        return file_record


class DeleteFileUseCase:
    def __init__(
        self,
        file_repository: FileRepository,
        storage_gateway: StorageGateway,
    ) -> None:
        self.file_repository = file_repository
        self.storage_gateway = storage_gateway

    async def execute(self, file_id: str) -> None:
        file_record = await self.file_repository.get_file(file_id)
        if file_record is None:
            raise FileNotFoundError("File not found")

        # Delete DB record first, then physical file.
        # If DB delete succeeds but physical delete fails, the record is gone
        # and the orphan file is harmless. The reverse order (physical first)
        # would leave a zombie DB record pointing to a missing file.
        await self.file_repository.delete_file(file_id)
        self.storage_gateway.delete_if_exists(file_record.stored_name)


class GetDownloadFileUseCase:
    def __init__(
        self,
        file_repository: FileRepository,
        storage_gateway: StorageGateway,
    ) -> None:
        self.file_repository = file_repository
        self.storage_gateway = storage_gateway

    async def execute(self, file_id: str) -> tuple[FileRecord, Path]:
        file_record = await self.file_repository.get_file(file_id)
        if file_record is None:
            raise FileNotFoundError("File not found")

        stored_path = self.storage_gateway.resolve_path(file_record.stored_name)
        if stored_path is None:
            raise StoredFileMissingError("Stored file not found")

        return file_record, stored_path
