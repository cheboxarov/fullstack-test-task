import pytest

from src.bootstrap.container import get_settings
from src.bootstrap.storage import get_storage_dir
from tests.support.worker_process import running_worker


def test_smoke_app_imports_and_exposes_routes(app):
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes}

    assert ("/files", ("GET",)) in paths
    assert ("/alerts", ("GET",)) in paths
    assert any(route.path == "/files/{file_id}/download" for route in app.routes)


def test_smoke_storage_override(storage_dir):
    assert get_storage_dir(get_settings()) == storage_dir
    assert storage_dir.exists()


@pytest.mark.slow
def test_smoke_worker_helper_can_start_and_stop(worker_env):
    with running_worker(env=worker_env(), timeout=20.0) as worker:
        assert worker.process.poll() is None
        assert "celery" in worker.output().lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("origin",),
    [
        ("http://localhost:3000",),
        ("http://127.0.0.1:3003",),
    ],
)
async def test_smoke_cors_allows_local_dev_origins(
    async_client, clean_database, origin: str
) -> None:
    response = await async_client.get("/files", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
