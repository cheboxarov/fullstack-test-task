"""SQLAlchemy file repository with cascade delete support."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.models import FileRecord
from src.infrastructure.mappers.orm_domain import stored_file_to_domain
from src.infrastructure.models import Alert, StoredFile


class SqlAlchemyFileRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    async def list_files(self) -> list[FileRecord]:
        async with self.session_maker() as session:
            result = await session.execute(
                select(StoredFile).order_by(StoredFile.created_at.desc())
            )
            return [
                stored_file_to_domain(file_row) for file_row in result.scalars().all()
            ]

    async def list_files_paginated(
        self, offset: int, limit: int
    ) -> tuple[list[FileRecord], int]:
        """Return paginated files with total count per D-04.

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (items, total_count)
        """
        async with self.session_maker() as session:
            # Get total count
            count_result = await session.execute(
                select(func.count()).select_from(StoredFile)
            )
            total = count_result.scalar() or 0

            # Get paginated items ordered by created_at desc (per D-02)
            result = await session.execute(
                select(StoredFile)
                .order_by(StoredFile.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            items = [
                stored_file_to_domain(file_row) for file_row in result.scalars().all()
            ]
            return items, total

    async def get_file(self, file_id: str) -> FileRecord | None:
        async with self.session_maker() as session:
            file_row = await session.get(StoredFile, file_id)
            if file_row is None:
                return None
            return stored_file_to_domain(file_row)

    async def insert_file(self, file_record: FileRecord) -> FileRecord:
        stored_file = StoredFile(
            id=file_record.id,
            title=file_record.title,
            original_name=file_record.original_name,
            stored_name=file_record.stored_name,
            mime_type=file_record.mime_type,
            size=file_record.size,
            processing_status=file_record.processing_status,
            scan_status=file_record.scan_status,
            scan_details=file_record.scan_details,
            metadata_json=file_record.metadata_json,
            requires_attention=file_record.requires_attention,
            created_at=file_record.created_at,
            updated_at=file_record.updated_at,
        )
        async with self.session_maker() as session:
            session.add(stored_file)
            await session.commit()
            await session.refresh(stored_file)
            return stored_file_to_domain(stored_file)

    async def update_title(self, file_id: str, title: str) -> FileRecord | None:
        async with self.session_maker() as session:
            file_row = await session.get(StoredFile, file_id)
            if file_row is None:
                return None
            file_row.title = title
            await session.commit()
            await session.refresh(file_row)
            return stored_file_to_domain(file_row)

    async def delete_file(self, file_id: str) -> FileRecord | None:
        """Delete file and all its dependent alerts atomically.

        This handles the FK constraint cascade at application level
        to avoid migration complexity (threat model T-03-04-01).
        """
        async with self.session_maker() as session:
            file_row = await session.get(StoredFile, file_id)
            if file_row is None:
                return None

            # Delete dependent alerts first (same transaction)
            await session.execute(delete(Alert).where(Alert.file_id == file_id))

            # Now delete the file
            file_record = stored_file_to_domain(file_row)
            await session.delete(file_row)
            await session.commit()
            return file_record

    async def save_scan_result(
        self,
        file_id: str,
        *,
        processing_status: str,
        scan_status: str | None,
        scan_details: str | None,
        requires_attention: bool,
    ) -> FileRecord | None:
        async with self.session_maker() as session:
            file_row = await session.get(StoredFile, file_id)
            if file_row is None:
                return None
            file_row.processing_status = processing_status
            file_row.scan_status = scan_status
            file_row.scan_details = scan_details
            file_row.requires_attention = requires_attention
            await session.commit()
            await session.refresh(file_row)
            return stored_file_to_domain(file_row)

    async def save_metadata_result(
        self,
        file_id: str,
        *,
        processing_status: str,
        metadata_json: dict[str, object] | None,
        scan_status: str | None = None,
        scan_details: str | None = None,
    ) -> FileRecord | None:
        async with self.session_maker() as session:
            file_row = await session.get(StoredFile, file_id)
            if file_row is None:
                return None
            file_row.processing_status = processing_status
            file_row.metadata_json = metadata_json
            if scan_status is not None:
                file_row.scan_status = scan_status
            if scan_details is not None:
                file_row.scan_details = scan_details
            await session.commit()
            await session.refresh(file_row)
            return stored_file_to_domain(file_row)
