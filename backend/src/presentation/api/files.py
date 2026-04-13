from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from src.application.use_cases.file_commands import (
    CreateFileUseCase,
    DeleteFileUseCase,
    GetDownloadFileUseCase,
    UpdateFileUseCase,
)
from src.application.use_cases.file_queries import (
    GetFileUseCase,
    ListFilesPaginatedUseCase,
    ListFilesUseCase,
)
from src.bootstrap.container import (
    get_create_file_use_case,
    get_delete_file_use_case,
    get_download_file_use_case,
    get_get_file_use_case,
    get_list_files_paginated_use_case,
    get_list_files_use_case,
    get_update_file_use_case,
)
from src.presentation.mappers.dto import domain_file_to_dto
from src.presentation.schemas import FileItem, FileUpdate, PaginatedResponse
from src.tasks import scan_file_for_threats


files_router = APIRouter()


@files_router.get("/files", response_model=PaginatedResponse[FileItem])
async def list_files_view(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    use_case: ListFilesPaginatedUseCase = Depends(get_list_files_paginated_use_case),
):
    """List files with pagination per D-01, D-03.

    Query parameters:
    - page: Page number (default: 1, minimum: 1)
    - page_size: Items per page (default: 10, min: 1, max: 100 per D-02)
    """
    items, total = await use_case.execute(page=page, page_size=page_size)
    return PaginatedResponse(
        items=[domain_file_to_dto(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@files_router.post("/files", response_model=FileItem, status_code=201)
async def create_file_view(
    title: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
    use_case: CreateFileUseCase = Depends(get_create_file_use_case),
):
    file_record = await use_case.execute(title=title, upload_file=file)
    file_item = domain_file_to_dto(file_record)
    scan_file_for_threats.delay(file_item.id)
    return file_item


@files_router.get("/files/{file_id}", response_model=FileItem)
async def get_file_view(
    file_id: str,
    use_case: GetFileUseCase = Depends(get_get_file_use_case),
):
    file_record = await use_case.execute(file_id)
    return domain_file_to_dto(file_record)


@files_router.patch("/files/{file_id}", response_model=FileItem)
async def update_file_view(
    file_id: str,
    payload: FileUpdate,
    use_case: UpdateFileUseCase = Depends(get_update_file_use_case),
):
    file_record = await use_case.execute(file_id=file_id, title=payload.title)
    return domain_file_to_dto(file_record)


@files_router.get("/files/{file_id}/download")
async def download_file_view(
    file_id: str,
    use_case: GetDownloadFileUseCase = Depends(get_download_file_use_case),
):
    file_record, stored_path = await use_case.execute(file_id)
    return FileResponse(
        path=stored_path,
        media_type=file_record.mime_type,
        filename=file_record.original_name,
    )


@files_router.delete("/files/{file_id}", status_code=204)
async def delete_file_view(
    file_id: str,
    use_case: DeleteFileUseCase = Depends(get_delete_file_use_case),
):
    await use_case.execute(file_id)
    return None
