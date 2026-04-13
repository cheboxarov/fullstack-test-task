from src.application.errors import FileNotFoundError
from src.application.ports import FileRepository
from src.domain.models import FileRecord


class ListFilesUseCase:
    def __init__(self, file_repository: FileRepository) -> None:
        self.file_repository = file_repository

    async def execute(self) -> list[FileRecord]:
        return await self.file_repository.list_files()


class ListFilesPaginatedUseCase:
    """Paginated file listing per D-01, D-02, D-03."""

    def __init__(self, file_repository: FileRepository) -> None:
        self.file_repository = file_repository

    async def execute(self, page: int, page_size: int) -> tuple[list[FileRecord], int]:
        """Execute paginated file query.

        Args:
            page: Page number (1-based, clamped to >= 1)
            page_size: Items per page (clamped 1-100 per D-02)

        Returns:
            Tuple of (file_records, total_count)
        """
        # Validate and clamp parameters per D-02, T-05-01-01, T-05-01-04
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:  # Per D-02 max, T-05-01-02 DoS prevention
            page_size = 100

        offset = (page - 1) * page_size
        items, total = await self.file_repository.list_files_paginated(
            offset, page_size
        )

        return items, total


class GetFileUseCase:
    def __init__(self, file_repository: FileRepository) -> None:
        self.file_repository = file_repository

    async def execute(self, file_id: str) -> FileRecord:
        file_record = await self.file_repository.get_file(file_id)
        if file_record is None:
            raise FileNotFoundError("File not found")
        return file_record
