from pathlib import Path
from typing import Protocol

from src.domain.models import AlertRecord, FileRecord


class FileRepository(Protocol):
    async def list_files(self) -> list[FileRecord]: ...

    async def list_files_paginated(
        self, offset: int, limit: int
    ) -> tuple[list[FileRecord], int]: ...

    """Returns (items, total_count) for pagination per D-04."""

    async def get_file(self, file_id: str) -> FileRecord | None: ...

    async def insert_file(self, file_record: FileRecord) -> FileRecord: ...

    async def update_title(self, file_id: str, title: str) -> FileRecord | None: ...

    async def delete_file(self, file_id: str) -> FileRecord | None: ...

    async def save_scan_result(
        self,
        file_id: str,
        *,
        processing_status: str,
        scan_status: str | None,
        scan_details: str | None,
        requires_attention: bool,
    ) -> FileRecord | None: ...

    async def save_metadata_result(
        self,
        file_id: str,
        *,
        processing_status: str,
        metadata_json: dict[str, object] | None,
        scan_status: str | None = None,
        scan_details: str | None = None,
    ) -> FileRecord | None: ...


class AlertRepository(Protocol):
    async def list_alerts(self) -> list[AlertRecord]: ...

    async def list_alerts_paginated(
        self, offset: int, limit: int
    ) -> tuple[list[AlertRecord], int]: ...

    """Returns (items, total_count) for pagination per D-04."""

    async def create_alert(
        self,
        *,
        file_id: str,
        level: str,
        message: str,
    ) -> AlertRecord: ...


class StorageGateway(Protocol):
    async def write_upload(
        self, file_id: str, upload_file: object, *, max_size_bytes: int | None = None
    ) -> tuple[str, str, int]: ...

    def resolve_path(self, stored_name: str) -> Path | None: ...

    def delete_if_exists(self, stored_name: str) -> None: ...

    def read_text(self, stored_name: str, encoding: str = "utf-8") -> str: ...

    def read_bytes(self, stored_name: str) -> bytes: ...
