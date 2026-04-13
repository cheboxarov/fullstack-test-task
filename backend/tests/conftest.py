import asyncio
import os
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.pool import NullPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
_UNSET = object()

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from src.bootstrap.container import (
    clear_test_overrides,
    get_engine,
    get_get_file_use_case,
    get_list_alerts_use_case,
    set_test_overrides,
)
from src.bootstrap.database import create_engine_from_settings, create_session_maker
from src.bootstrap.settings import load_settings


os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("PGPORT", "5433")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", os.environ["REDIS_URL"])
os.environ.setdefault("CELERY_QUEUE", "file-processing-tests")


import src.app as app_module
import src.presentation.api.files as files_api_module
from src.infrastructure.models import Base
import src.tasks as tasks_module


def _run_checked(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        command,
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _run_capture(command: list[str]) -> str:
    return subprocess.check_output(command, text=True).strip()


async def _truncate_tables() -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text("TRUNCATE TABLE alerts, files RESTART IDENTITY CASCADE")
        )


class BackendPoller:
    def __init__(self, poll_interval: float = 0.2):
        self.poll_interval = poll_interval

    async def wait_for_file_state(
        self,
        file_id: str,
        *,
        timeout: float = 10.0,
        processing_status: Any = _UNSET,
        scan_status: Any = _UNSET,
        requires_attention: Any = _UNSET,
    ):
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None

        while time.monotonic() < deadline:
            try:
                file_item = await get_get_file_use_case().execute(file_id)
            except Exception as exc:  # pragma: no cover - poll retries intentionally
                last_error = exc
            else:
                if (
                    processing_status is not _UNSET
                    and file_item.processing_status != processing_status
                ):
                    pass
                elif scan_status is not _UNSET and file_item.scan_status != scan_status:
                    pass
                elif (
                    requires_attention is not _UNSET
                    and file_item.requires_attention != requires_attention
                ):
                    pass
                else:
                    return file_item

            await asyncio.sleep(self.poll_interval)

        if last_error is not None:
            raise AssertionError(
                f"Timed out waiting for file state for {file_id}: {last_error}"
            ) from last_error

        raise AssertionError(f"Timed out waiting for file state for {file_id}")

    async def wait_for_alert_count(
        self, file_id: str, expected_count: int, *, timeout: float = 10.0
    ):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            alerts = await get_list_alerts_use_case().execute()
            matching_alerts = [alert for alert in alerts if alert.file_id == file_id]
            if len(matching_alerts) == expected_count:
                return matching_alerts

            await asyncio.sleep(self.poll_interval)

        raise AssertionError(
            f"Timed out waiting for {expected_count} alert(s) for {file_id}"
        )


@pytest.fixture(scope="session")
def database_ready(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    tmp_path_factory.mktemp("pg-data")
    container_name = f"backend-test-db-{uuid.uuid4().hex[:10]}"
    queue_name = f"file-processing-tests-{uuid.uuid4().hex[:8]}"
    _run_checked(
        [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            container_name,
            "-e",
            f"POSTGRES_USER={os.environ['POSTGRES_USER']}",
            "-e",
            f"POSTGRES_PASSWORD={os.environ['POSTGRES_PASSWORD']}",
            "-e",
            f"POSTGRES_DB={os.environ['POSTGRES_DB']}",
            "-p",
            "127.0.0.1::5432",
            "postgres:latest",
        ]
    )

    port_line = _run_capture(["docker", "port", container_name, "5432/tcp"])
    port = port_line.rsplit(":", 1)[1]

    deadline = time.monotonic() + 30
    ready = False
    while time.monotonic() < deadline:
        probe = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "pg_isready",
                "-U",
                os.environ["POSTGRES_USER"],
                "-d",
                os.environ["POSTGRES_DB"],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if probe.returncode == 0:
            ready = True
            break
        time.sleep(0.5)

    if not ready:
        logs = _run_capture(["docker", "logs", container_name])
        raise RuntimeError(
            f"Timed out waiting for disposable Postgres container:\n{logs}"
        )

    db_url = (
        f"postgresql+asyncpg://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@127.0.0.1:{port}/{os.environ['POSTGRES_DB']}"
    )

    os.environ["POSTGRES_HOST"] = "127.0.0.1"
    os.environ["PGPORT"] = str(port)
    os.environ["CELERY_QUEUE"] = queue_name

    clear_test_overrides()
    settings_model = load_settings()
    engine = create_engine_from_settings(
        settings_model,
        poolclass=NullPool,
        connect_args={"ssl": False},
    )
    session_maker = create_session_maker(engine)
    set_test_overrides(
        settings=settings_model,
        engine=engine,
        session_maker=session_maker,
    )
    tasks_module.DB_URL = db_url
    tasks_module.engine = engine
    tasks_module.async_session_maker = session_maker
    tasks_module.CELERY_QUEUE = queue_name
    tasks_module.celery_app.conf.broker_url = os.environ.get(
        "REDIS_URL", os.environ.get("CELERY_BROKER_URL", "")
    )
    tasks_module.celery_app.conf.result_backend = (
        tasks_module.celery_app.conf.broker_url
    )
    tasks_module.celery_app.conf.task_default_queue = queue_name
    tasks_module.celery_app.conf.task_default_exchange = queue_name
    tasks_module.celery_app.conf.task_default_routing_key = queue_name

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    last_schema_error: Exception | None = None
    for _ in range(20):
        try:
            asyncio.run(create_schema())
        except (
            Exception
        ) as exc:  # pragma: no cover - startup race is environment-dependent
            last_schema_error = exc
            time.sleep(0.5)
        else:
            last_schema_error = None
            break

    if last_schema_error is not None:
        raise RuntimeError(
            f"Timed out creating schema against disposable Postgres: {last_schema_error}"
        ) from last_schema_error

    settings = {
        "host": "127.0.0.1",
        "port": str(port),
        "db_url": db_url,
        "celery_queue": queue_name,
    }

    yield settings

    clear_test_overrides()
    asyncio.run(engine.dispose())
    _run_checked(["docker", "rm", "-f", container_name])


@pytest.fixture()
async def clean_database(database_ready) -> AsyncIterator[None]:
    await _truncate_tables()
    yield
    await _truncate_tables()


@pytest.fixture()
def app():
    return app_module.app


@pytest.fixture(autouse=True)
def storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    storage_path = tmp_path / "files"
    storage_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("STORAGE_DIR", str(storage_path))
    set_test_overrides(storage_dir=storage_path)

    return storage_path


@pytest.fixture(autouse=True)
def queue_backend_tasks(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
):
    if request.node.get_closest_marker("real_worker"):
        return None

    class QueueStub:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def delay(self, file_id: str) -> None:
            self.calls.append(file_id)

    queue_stub = QueueStub()
    monkeypatch.setattr(files_api_module, "scan_file_for_threats", queue_stub)
    return queue_stub


@pytest.fixture()
async def async_client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture()
def poller() -> BackendPoller:
    return BackendPoller()


@pytest.fixture()
def worker_env(storage_dir: Path) -> Callable[[dict[str, str] | None], dict[str, str]]:
    def factory(extra_env: dict[str, str] | None = None) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "POSTGRES_USER": os.environ["POSTGRES_USER"],
                "POSTGRES_PASSWORD": os.environ["POSTGRES_PASSWORD"],
                "POSTGRES_DB": os.environ["POSTGRES_DB"],
                "POSTGRES_HOST": os.environ["POSTGRES_HOST"],
                "PGPORT": os.environ["PGPORT"],
                "REDIS_URL": os.environ["REDIS_URL"],
                "CELERY_BROKER_URL": os.environ["CELERY_BROKER_URL"],
                "CELERY_QUEUE": os.environ["CELERY_QUEUE"],
                "STORAGE_DIR": str(storage_dir),
                "PYTHONPATH": str(BACKEND_DIR),
            }
        )
        if extra_env:
            env.update(extra_env)
        return env

    return factory
