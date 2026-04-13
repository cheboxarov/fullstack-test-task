from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.application.orchestration.pipeline_orchestrator import PipelineOrchestrator
from src.application.use_cases.alert_queries import (
    ListAlertsPaginatedUseCase,
    ListAlertsUseCase,
)
from src.application.use_cases.file_commands import (
    CreateFileUseCase,
    DeleteFileUseCase,
    GetDownloadFileUseCase,
    UpdateFileUseCase,
)
from src.application.use_cases.file_processing import (
    ExtractFileMetadataUseCase,
    ScanFileForThreatsUseCase,
    SendFileAlertUseCase,
)
from src.application.use_cases.file_queries import (
    GetFileUseCase,
    ListFilesPaginatedUseCase,
    ListFilesUseCase,
)
from src.bootstrap.database import create_engine_from_settings, create_session_maker
from src.bootstrap.settings import Settings, load_settings
from src.bootstrap.storage import get_storage_dir
from src.infrastructure.repositories.sqlalchemy_alert_repository import (
    SqlAlchemyAlertRepository,
)
from src.infrastructure.repositories.sqlalchemy_file_repository import (
    SqlAlchemyFileRepository,
)
from src.infrastructure.storage.local_file_storage import LocalFileStorage
from src.application.worker.event_loop import run_in_worker_loop


@dataclass(slots=True)
class BootstrapOverrides:
    settings: Settings | None = None
    engine: Any = None
    session_maker: Any = None


_overrides = BootstrapOverrides()
_settings_cache: Settings | None = None
_engine_cache: AsyncEngine | None = None
_session_maker_cache: async_sessionmaker[AsyncSession] | None = None


def get_settings() -> Settings:
    global _settings_cache

    if _overrides.settings is not None:
        return _overrides.settings

    if _settings_cache is None:
        _settings_cache = load_settings()
    return _settings_cache


def get_engine() -> AsyncEngine | Any:
    global _engine_cache

    if _overrides.engine is not None:
        return _overrides.engine

    if _engine_cache is None:
        _engine_cache = create_engine_from_settings(get_settings())
    return _engine_cache


def get_session_maker() -> async_sessionmaker[AsyncSession] | Any:
    global _session_maker_cache

    if _overrides.session_maker is not None:
        return _overrides.session_maker

    if _session_maker_cache is None:
        _session_maker_cache = create_session_maker(get_engine())
    return _session_maker_cache


def set_test_overrides(
    *,
    settings: Settings | None = None,
    engine: Any | None = None,
    session_maker: Any | None = None,
    storage_dir: Any | None = None,
) -> None:
    if settings is not None and storage_dir is not None:
        settings = replace(settings, storage_dir=storage_dir)
    elif settings is None and storage_dir is not None:
        settings = replace(
            _overrides.settings or get_settings(), storage_dir=storage_dir
        )

    if settings is not None:
        _overrides.settings = settings
    if engine is not None:
        _overrides.engine = engine
    if session_maker is not None:
        _overrides.session_maker = session_maker


def clear_test_overrides() -> None:
    global _settings_cache, _engine_cache, _session_maker_cache

    _overrides.settings = None
    _overrides.engine = None
    _overrides.session_maker = None
    _settings_cache = None
    _engine_cache = None
    _session_maker_cache = None


def get_file_repository() -> SqlAlchemyFileRepository:
    return SqlAlchemyFileRepository(get_session_maker())


def get_alert_repository() -> SqlAlchemyAlertRepository:
    return SqlAlchemyAlertRepository(get_session_maker())


def get_storage_gateway() -> LocalFileStorage:
    return LocalFileStorage(get_storage_dir(get_settings()))


def get_list_files_use_case() -> ListFilesUseCase:
    return ListFilesUseCase(get_file_repository())


def get_list_files_paginated_use_case() -> ListFilesPaginatedUseCase:
    """Provider for paginated file listing per D-01."""
    return ListFilesPaginatedUseCase(get_file_repository())


def get_list_alerts_use_case() -> ListAlertsUseCase:
    return ListAlertsUseCase(get_alert_repository())


def get_list_alerts_paginated_use_case() -> ListAlertsPaginatedUseCase:
    """Provider for paginated alert listing per D-01."""
    return ListAlertsPaginatedUseCase(get_alert_repository())


def get_get_file_use_case() -> GetFileUseCase:
    return GetFileUseCase(get_file_repository())


def get_create_file_use_case() -> CreateFileUseCase:
    settings = get_settings()
    return CreateFileUseCase(
        get_file_repository(),
        get_storage_gateway(),
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


def get_update_file_use_case() -> UpdateFileUseCase:
    return UpdateFileUseCase(get_file_repository())


def get_delete_file_use_case() -> DeleteFileUseCase:
    return DeleteFileUseCase(get_file_repository(), get_storage_gateway())


def get_download_file_use_case() -> GetDownloadFileUseCase:
    return GetDownloadFileUseCase(get_file_repository(), get_storage_gateway())


def get_scan_file_for_threats_use_case() -> ScanFileForThreatsUseCase:
    return ScanFileForThreatsUseCase(get_file_repository())


def get_extract_file_metadata_use_case() -> ExtractFileMetadataUseCase:
    return ExtractFileMetadataUseCase(get_file_repository(), get_storage_gateway())


def get_send_file_alert_use_case() -> SendFileAlertUseCase:
    return SendFileAlertUseCase(get_file_repository(), get_alert_repository())


def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """Provider for PipelineOrchestrator with all use case dependencies.

    Creates PipelineOrchestrator configured with:
    - scan_file_for_threats use case
    - extract_file_metadata use case
    - send_file_alert use case

    Returns:
        Configured PipelineOrchestrator instance
    """
    return PipelineOrchestrator()
