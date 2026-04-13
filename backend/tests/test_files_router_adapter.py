import pytest

import src.presentation.api.files as files_api_module


pytestmark = pytest.mark.usefixtures("clean_database")


@pytest.mark.asyncio
async def test_files_router_uses_container_overrides_and_enqueues_after_persist(
    async_client,
    storage_dir,
    monkeypatch: pytest.MonkeyPatch,
):
    class QueueStub:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def delay(self, file_id: str) -> None:
            self.calls.append(file_id)

    queue_stub = QueueStub()
    monkeypatch.setattr(files_api_module, "scan_file_for_threats", queue_stub)

    response = await async_client.post(
        "/files",
        data={"title": "Router upload"},
        files={"file": ("router.txt", b"router-data", "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert queue_stub.calls == [payload["id"]]
    assert (storage_dir / f"{payload['id']}.txt").exists()
