from pathlib import Path

import pytest
from sqlalchemy import text

from src.bootstrap.container import get_session_maker
from src.infrastructure.models import Alert


pytestmark = pytest.mark.usefixtures("clean_database")


FILE_ITEM_FIELDS = {
    "id",
    "title",
    "original_name",
    "mime_type",
    "size",
    "processing_status",
    "scan_status",
    "scan_details",
    "metadata_json",
    "requires_attention",
    "created_at",
    "updated_at",
}

ALERT_ITEM_FIELDS = {"id", "file_id", "level", "message", "created_at"}


@pytest.mark.asyncio
async def test_create_file_returns_current_contract_shape(async_client, storage_dir):
    response = await async_client.post(
        "/files",
        data={"title": "Quarterly report"},
        files={"file": ("report.txt", b"hello\nworld\n", "text/plain")},
    )

    assert response.status_code == 201

    payload = response.json()
    assert set(payload) == FILE_ITEM_FIELDS
    assert payload["title"] == "Quarterly report"
    assert payload["original_name"] == "report.txt"
    assert payload["mime_type"] == "text/plain"
    assert payload["size"] == 12
    assert payload["processing_status"] == "uploaded"
    assert payload["scan_status"] is None
    assert payload["scan_details"] is None
    assert payload["metadata_json"] is None
    assert payload["requires_attention"] is False
    assert Path(storage_dir, f"{payload['id']}.txt").exists()


@pytest.mark.asyncio
async def test_empty_upload_returns_current_400(async_client):
    response = await async_client.post(
        "/files",
        data={"title": "Empty"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"] == "empty_upload"
    assert payload["error"]["retryable"] is False
    assert "request_id" in payload["error"]


@pytest.mark.asyncio
async def test_get_files_returns_empty_list(async_client):
    response = await async_client.get("/files")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["pages"] == 0


@pytest.mark.asyncio
async def test_get_alerts_returns_empty_list(async_client):
    response = await async_client.get("/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["pages"] == 0


@pytest.mark.asyncio
async def test_file_crud_happy_path_and_missing_row_errors(async_client, storage_dir):
    create_response = await async_client.post(
        "/files",
        data={"title": "Original title"},
        files={"file": ("notes.txt", b"line one\nline two\n", "text/plain")},
    )
    file_id = create_response.json()["id"]

    get_response = await async_client.get(f"/files/{file_id}")
    assert get_response.status_code == 200
    assert set(get_response.json()) == FILE_ITEM_FIELDS

    patch_response = await async_client.patch(
        f"/files/{file_id}",
        json={"title": "Renamed title"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Renamed title"

    download_response = await async_client.get(f"/files/{file_id}/download")
    assert download_response.status_code == 200
    assert download_response.content == b"line one\nline two\n"
    assert (
        'attachment; filename="notes.txt"'
        in download_response.headers["content-disposition"]
    )

    delete_response = await async_client.delete(f"/files/{file_id}")
    assert delete_response.status_code == 204
    assert not Path(storage_dir, f"{file_id}.txt").exists()

    for method, path, payload in [
        ("get", "/files/missing-file", None),
        ("patch", "/files/missing-file", {"title": "still missing"}),
        ("delete", "/files/missing-file", None),
    ]:
        request_kwargs = {"json": payload} if payload is not None else {}
        response = await getattr(async_client, method)(path, **request_kwargs)
        assert response.status_code == 404
        resp_payload = response.json()
        assert "error" in resp_payload
        assert resp_payload["error"]["code"] == "file_not_found"
        assert "request_id" in resp_payload["error"]


@pytest.mark.asyncio
async def test_download_returns_stored_file_not_found_when_disk_file_is_missing(
    async_client,
    storage_dir,
):
    create_response = await async_client.post(
        "/files",
        data={"title": "Ghost file"},
        files={"file": ("ghost.txt", b"ghost", "text/plain")},
    )
    payload = create_response.json()

    missing_path = Path(storage_dir, f"{payload['id']}.txt")
    missing_path.unlink()

    response = await async_client.get(f"/files/{payload['id']}/download")

    assert response.status_code == 404
    resp_payload = response.json()
    assert "error" in resp_payload
    assert resp_payload["error"]["code"] == "stored_file_missing"
    assert "request_id" in resp_payload["error"]


@pytest.mark.asyncio
async def test_files_are_returned_in_created_at_desc_order(async_client):
    older = await async_client.post(
        "/files",
        data={"title": "Older"},
        files={"file": ("older.txt", b"older", "text/plain")},
    )
    newer = await async_client.post(
        "/files",
        data={"title": "Newer"},
        files={"file": ("newer.txt", b"newer", "text/plain")},
    )

    response = await async_client.get("/files")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [
        newer.json()["id"],
        older.json()["id"],
    ]


@pytest.mark.asyncio
async def test_alerts_are_returned_in_created_at_desc_order(
    async_client, clean_database
):
    first = await async_client.post(
        "/files",
        data={"title": "First"},
        files={"file": ("first.txt", b"first", "text/plain")},
    )
    second = await async_client.post(
        "/files",
        data={"title": "Second"},
        files={"file": ("second.txt", b"second", "text/plain")},
    )

    async with get_session_maker()() as session:
        session.add_all(
            [
                Alert(file_id=first.json()["id"], level="info", message="first alert"),
                Alert(
                    file_id=second.json()["id"], level="warning", message="second alert"
                ),
            ]
        )
        await session.commit()
        await session.execute(
            text(
                "UPDATE alerts SET created_at = now() - interval '1 minute' WHERE file_id = :file_id"
            ),
            {"file_id": first.json()["id"]},
        )
        await session.execute(
            text("UPDATE alerts SET created_at = now() WHERE file_id = :file_id"),
            {"file_id": second.json()["id"]},
        )
        await session.commit()

    response = await async_client.get("/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert set(payload["items"][0]) == ALERT_ITEM_FIELDS
    assert set(payload["items"][1]) == ALERT_ITEM_FIELDS
    assert [item["file_id"] for item in payload["items"]] == [
        second.json()["id"],
        first.json()["id"],
    ]
