import ast
from datetime import datetime, timezone
from pathlib import Path

from src.bootstrap.container import (
    clear_test_overrides,
    get_engine,
    get_session_maker,
    get_settings,
    set_test_overrides,
)
from src.bootstrap.database import build_db_url
from src.bootstrap.settings import Settings, load_settings
from src.bootstrap.storage import get_storage_dir
from src.application import errors as application_errors
from src.application import ports
from src.infrastructure.mappers.orm_domain import alert_to_domain, stored_file_to_domain
from src.infrastructure.models import Alert, StoredFile
from src.presentation.mappers.dto import domain_alert_to_dto, domain_file_to_dto


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _read_backend_file(relative_path: str) -> str:
    return (BACKEND_DIR / relative_path).read_text(encoding="utf-8")


def test_domain_models_and_mappers_preserve_contract_fields() -> None:
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc)

    stored_file = StoredFile(
        id="file-1",
        title="Quarterly report",
        original_name="report.pdf",
        stored_name="file-1.pdf",
        mime_type="application/pdf",
        size=128,
        processing_status="processed",
        scan_status="clean",
        scan_details="no threats found",
        metadata_json={"pages": 3},
        requires_attention=False,
        created_at=created_at,
        updated_at=updated_at,
    )
    alert = Alert(
        id=10,
        file_id="file-1",
        level="info",
        message="File processed successfully",
        created_at=created_at,
    )

    file_record = stored_file_to_domain(stored_file)
    alert_record = alert_to_domain(alert)
    file_dto = domain_file_to_dto(file_record)
    alert_dto = domain_alert_to_dto(alert_record)

    assert file_record.stored_name == stored_file.stored_name
    assert file_dto.model_dump() == {
        "id": "file-1",
        "title": "Quarterly report",
        "original_name": "report.pdf",
        "mime_type": "application/pdf",
        "size": 128,
        "processing_status": "processed",
        "scan_status": "clean",
        "scan_details": "no threats found",
        "metadata_json": {"pages": 3},
        "requires_attention": False,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    assert alert_dto.model_dump() == {
        "id": 10,
        "file_id": "file-1",
        "level": "info",
        "message": "File processed successfully",
        "created_at": created_at,
    }


def test_application_ports_do_not_import_fastapi_or_sqlalchemy_models() -> None:
    ports_source = ports.__file__
    errors_source = application_errors.__file__

    assert ports_source is not None
    assert errors_source is not None

    with open(ports_source, encoding="utf-8") as file_obj:
        ports_text = file_obj.read()
    with open(errors_source, encoding="utf-8") as file_obj:
        errors_text = file_obj.read()

    ports_tree = ast.parse(ports_text)
    errors_tree = ast.parse(errors_text)

    port_import_modules = {
        node.module for node in ast.walk(ports_tree) if isinstance(node, ast.ImportFrom)
    }
    port_import_names = {
        alias.name
        for node in ast.walk(ports_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    error_import_modules = {
        node.module
        for node in ast.walk(errors_tree)
        if isinstance(node, ast.ImportFrom)
    }
    error_import_names = {
        alias.name
        for node in ast.walk(errors_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }

    assert "fastapi" not in ports_text
    assert "UploadFile" not in ports_text
    assert "HTTPException" not in ports_text
    assert "fastapi" not in errors_text
    assert "HTTPException" not in errors_text
    assert "src.models" not in port_import_modules
    assert "src.models" not in error_import_modules
    assert "StoredFile" not in port_import_names
    assert "Alert" not in port_import_names
    assert "UploadFile" not in port_import_names
    assert "HTTPException" not in port_import_names
    assert "HTTPException" not in error_import_names


def test_settings_db_url_storage_and_container_overrides_preserve_existing_semantics(
    monkeypatch, tmp_path: Path
) -> None:
    storage_dir = tmp_path / "uploads"
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("PGPORT", "5439")
    monkeypatch.setenv("POSTGRES_DB", "files")
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/1")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/2")
    monkeypatch.setenv("CELERY_QUEUE", "architecture-tests")

    clear_test_overrides()
    settings = load_settings()

    assert (
        build_db_url(settings)
        == "postgresql+asyncpg://postgres:secret@db.internal:5439/files"
    )
    assert settings.redis_url == "redis://cache:6379/1"
    assert settings.celery_broker_url == "redis://broker:6379/2"
    assert settings.celery_queue == "architecture-tests"
    assert get_storage_dir(settings) == storage_dir
    assert storage_dir.exists()


def test_container_supports_test_overrides_without_service_global_mutation(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("STORAGE_DIR", raising=False)

    clear_test_overrides()

    baseline_settings = get_settings()
    baseline_db_url = build_db_url(baseline_settings)

    override_settings = Settings(
        postgres_user="override-user",
        postgres_password="override-password",
        postgres_host="override-host",
        postgres_port="5544",
        postgres_db="override-db",
        storage_dir=tmp_path / "override-storage",
        redis_url="redis://override-cache:6379/3",
        celery_broker_url="redis://override-broker:6379/4",
        celery_queue="override-queue",
        max_upload_size_bytes=10 * 1024 * 1024,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )
    override_engine = object()
    override_session_maker = object()

    set_test_overrides(
        settings=override_settings,
        engine=override_engine,
        session_maker=override_session_maker,
    )

    assert get_settings() is override_settings
    assert get_engine() is override_engine
    assert get_session_maker() is override_session_maker
    assert (
        build_db_url(get_settings())
        == "postgresql+asyncpg://override-user:override-password@override-host:5544/override-db"
    )
    assert build_db_url(baseline_settings) == baseline_db_url

    clear_test_overrides()
    assert get_settings() is not override_settings


def test_settings_default_celery_queue_is_project_specific(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("PGPORT", "5439")
    monkeypatch.setenv("POSTGRES_DB", "files")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/1")
    monkeypatch.delenv("CELERY_QUEUE", raising=False)

    clear_test_overrides()
    settings = load_settings()

    assert settings.celery_queue == "file-processing-mvp"


def test_entrypoints_and_tests_no_longer_import_service_module() -> None:
    guarded_files = {
        "src/app.py": _read_backend_file("src/app.py"),
        "src/tasks.py": _read_backend_file("src/tasks.py"),
        "migrations/env.py": _read_backend_file("migrations/env.py"),
        "tests/conftest.py": _read_backend_file("tests/conftest.py"),
        "tests/test_smoke_contract.py": _read_backend_file(
            "tests/test_smoke_contract.py"
        ),
    }

    for relative_path, source_text in guarded_files.items():
        assert "src.service" not in source_text, relative_path


def test_service_module_is_deleted_or_thin_shim_only() -> None:
    service_path = BACKEND_DIR / "src/service.py"
    if not service_path.exists():
        return

    source_text = service_path.read_text(encoding="utf-8")
    non_empty_lines = [line for line in source_text.splitlines() if line.strip()]

    assert len(non_empty_lines) <= 40
    assert "create_async_engine(" not in source_text
    assert "async_session_maker =" not in source_text
    assert "HTTPException" not in source_text
    assert "UploadFile" not in source_text

    for function_name in [
        "list_files",
        "list_alerts",
        "get_file",
        "create_file",
        "update_file",
        "delete_file",
        "get_file_path",
        "create_alert",
    ]:
        assert f"def {function_name}(" not in source_text
        assert f"async def {function_name}(" not in source_text


def test_alembic_uses_bootstrap_db_url_builder() -> None:
    env_source = _read_backend_file("migrations/env.py")

    assert "from src.service import DB_URL" not in env_source
    assert "load_settings" in env_source
    assert "build_db_url" in env_source
