"""Tests for delete cascade with dependent alerts."""

import pytest
from sqlalchemy import select

from src.bootstrap.container import get_session_maker
from src.infrastructure.models import Alert, StoredFile

pytestmark = pytest.mark.usefixtures("clean_database")


@pytest.mark.asyncio
async def test_delete_file_with_alerts_removes_both(async_client, storage_dir):
    """DELETE /files/{id} should remove file and all its alerts."""
    # Create a file
    response = await async_client.post(
        "/files",
        data={"title": "File with alerts"},
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Create alerts for the file directly in DB
    async with get_session_maker()() as session:
        session.add_all(
            [
                Alert(file_id=file_id, level="info", message="First alert"),
                Alert(file_id=file_id, level="warning", message="Second alert"),
                Alert(file_id=file_id, level="critical", message="Third alert"),
            ]
        )
        await session.commit()

    # Verify alerts exist
    async with get_session_maker()() as session:
        result = await session.execute(select(Alert).where(Alert.file_id == file_id))
        alerts = result.scalars().all()
        assert len(alerts) == 3, "Should have 3 alerts before delete"

    # Delete the file
    delete_response = await async_client.delete(f"/files/{file_id}")
    assert delete_response.status_code == 204

    # Verify file is gone
    get_response = await async_client.get(f"/files/{file_id}")
    assert get_response.status_code == 404

    # Verify alerts are also gone
    async with get_session_maker()() as session:
        result = await session.execute(select(Alert).where(Alert.file_id == file_id))
        alerts_after = result.scalars().all()
        assert len(alerts_after) == 0, "All alerts should be deleted with the file"


@pytest.mark.asyncio
async def test_delete_file_without_alerts_still_works(async_client, storage_dir):
    """DELETE /files/{id} should work for files with no alerts."""
    # Create a file
    response = await async_client.post(
        "/files",
        data={"title": "File without alerts"},
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Delete the file (should succeed even without alerts)
    delete_response = await async_client.delete(f"/files/{file_id}")
    assert delete_response.status_code == 204

    # Verify file is gone
    get_response = await async_client.get(f"/files/{file_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_file_returns_404(async_client):
    """DELETE /files/{nonexistent-id} should return 404."""
    response = await async_client.delete("/files/nonexistent-file-id")
    assert response.status_code == 404
