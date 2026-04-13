from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from src.application.errors import FileNotFoundError, StoredFileMissingError
from src.application.use_cases.file_commands import (
    CreateFileUseCase,
    DeleteFileUseCase,
    GetDownloadFileUseCase,
)
from src.application.use_cases.file_queries import GetFileUseCase, ListFilesUseCase
from src.bootstrap.container import get_session_maker
from src.domain.models import FileRecord
from src.infrastructure.repositories.sqlalchemy_file_repository import (
    SqlAlchemyFileRepository,
)
from src.infrastructure.storage.local_file_storage import LocalFileStorage


pytestmark = pytest.mark.usefixtures("clean_database")


class UploadStub:
    def __init__(
        self,
        *,
        filename: str | None,
        content: bytes,
        content_type: str | None,
    ) -> None:
        self.filename = filename
        self._content = content
        self.content_type = content_type
        self.size = len(content)
        self.read_calls = 0
        self._read_offset = 0

    async def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if size <= 0:
            # Return remaining content and reset for next call
            remaining = self._content[self._read_offset :]
            self._read_offset = 0
            return remaining
        # Return chunk of specified size (simulating streaming)
        chunk = self._content[self._read_offset : self._read_offset + size]
        self._read_offset += len(chunk)
        return chunk


def build_file_repository() -> SqlAlchemyFileRepository:
    return SqlAlchemyFileRepository(get_session_maker())


def build_storage_gateway(storage_dir: Path) -> LocalFileStorage:
    return LocalFileStorage(storage_dir)


@pytest.mark.asyncio
async def test_create_uploaded_file_preserves_current_uploaded_state(storage_dir: Path):
    file_repository = build_file_repository()
    storage_gateway = build_storage_gateway(storage_dir)
    use_case = CreateFileUseCase(file_repository, storage_gateway)
    upload = UploadStub(
        filename="report.txt",
        content=b"hello\nworld\n",
        content_type=None,
    )

    created_file = await use_case.execute(title="Quarterly report", upload_file=upload)

    assert upload.read_calls >= 1  # Chunked read may call read multiple times
    assert created_file.title == "Quarterly report"
    assert created_file.original_name == "report.txt"
    assert created_file.stored_name == f"{created_file.id}.txt"
    assert created_file.mime_type == "text/plain"
    assert created_file.size == 12
    assert created_file.processing_status == "uploaded"
    assert created_file.scan_status is None
    assert created_file.scan_details is None
    assert created_file.metadata_json is None
    assert created_file.requires_attention is False
    assert (storage_dir / created_file.stored_name).read_bytes() == b"hello\nworld\n"


@pytest.mark.asyncio
async def test_list_and_get_file_use_cases_preserve_desc_order_and_missing_row_behavior():
    file_repository = build_file_repository()
    list_use_case = ListFilesUseCase(file_repository)
    get_use_case = GetFileUseCase(file_repository)
    base_time = datetime.now(timezone.utc)
    older_file = FileRecord(
        id="older-file",
        title="Older",
        original_name="older.txt",
        stored_name="older-file.txt",
        mime_type="text/plain",
        size=5,
        processing_status="uploaded",
        scan_status=None,
        scan_details=None,
        metadata_json=None,
        requires_attention=False,
        created_at=base_time - timedelta(minutes=1),
        updated_at=base_time - timedelta(minutes=1),
    )
    newer_file = replace(
        older_file,
        id="newer-file",
        title="Newer",
        original_name="newer.txt",
        stored_name="newer-file.txt",
        created_at=base_time,
        updated_at=base_time,
    )
    await file_repository.insert_file(older_file)
    await file_repository.insert_file(newer_file)

    listed_files = await list_use_case.execute()
    loaded_file = await get_use_case.execute(newer_file.id)

    assert [file_item.id for file_item in listed_files] == [
        newer_file.id,
        older_file.id,
    ]
    assert loaded_file.id == newer_file.id

    with pytest.raises(FileNotFoundError, match="File not found"):
        await get_use_case.execute("missing-file")


@pytest.mark.asyncio
async def test_download_and_delete_use_cases_preserve_current_storage_path_behavior(
    storage_dir: Path,
):
    file_repository = build_file_repository()
    storage_gateway = build_storage_gateway(storage_dir)
    create_use_case = CreateFileUseCase(file_repository, storage_gateway)
    download_use_case = GetDownloadFileUseCase(file_repository, storage_gateway)
    delete_use_case = DeleteFileUseCase(file_repository, storage_gateway)
    upload = UploadStub(
        filename="notes.txt",
        content=b"line one\nline two\n",
        content_type="text/plain",
    )

    created_file = await create_use_case.execute(title="Notes", upload_file=upload)
    stored_path = storage_dir / created_file.stored_name

    loaded_file, download_path = await download_use_case.execute(created_file.id)

    assert loaded_file.id == created_file.id
    assert download_path == stored_path

    stored_path.unlink()

    with pytest.raises(StoredFileMissingError, match="Stored file not found"):
        await download_use_case.execute(created_file.id)

    await delete_use_case.execute(created_file.id)

    assert await file_repository.get_file(created_file.id) is None
