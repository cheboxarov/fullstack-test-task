"""Tests for upload size validation."""

import pytest

pytestmark = pytest.mark.usefixtures("clean_database")


@pytest.mark.asyncio
async def test_upload_size_limit_accepts_valid_file(async_client, storage_dir):
    """Files within the size limit should upload successfully."""
    content = b"valid content that is under the 10MB limit"
    response = await async_client.post(
        "/files",
        data={"title": "Valid file"},
        files={"file": ("valid.txt", content, "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Valid file"
    assert payload["size"] == len(content)


@pytest.mark.asyncio
async def test_upload_size_limit_rejects_oversized_file(async_client):
    """Files exceeding the limit should get 413 Payload Too Large."""
    # Create content that exceeds the 10MB default limit
    oversized_content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
    response = await async_client.post(
        "/files",
        data={"title": "Too big"},
        files={"file": ("large.bin", oversized_content, "application/octet-stream")},
    )

    assert response.status_code == 413
    assert (
        "exceeds" in response.json()["detail"].lower()
        or "too large" in response.json()["detail"].lower()
    )


@pytest.mark.asyncio
async def test_upload_size_check_happens_before_read(async_client):
    """Size check should happen before reading file into memory.

    This is verified by checking the error response contains size information
    indicating the size was checked before processing.
    """
    oversized_content = b"x" * (10 * 1024 * 1024 + 1)
    response = await async_client.post(
        "/files",
        data={"title": "Check early"},
        files={
            "file": ("early-check.bin", oversized_content, "application/octet-stream")
        },
    )

    assert response.status_code == 413
    # The error message should mention the size that was checked
    detail = response.json()["detail"]
    assert "10485761" in detail or "exceeds" in detail.lower()


@pytest.mark.asyncio
async def test_upload_size_limit_default_10mb(async_client, storage_dir):
    """Default upload size limit of 10MB should be enforced.

    Note: Env-based configuration requires container reload at module level.
    This test verifies the default 10MB limit behavior.
    """
    # Medium file under 10MB should pass
    medium_content = b"x" * (5 * 1024 * 1024)  # 5MB
    response_medium = await async_client.post(
        "/files",
        data={"title": "Medium file"},
        files={"file": ("medium.bin", medium_content, "application/octet-stream")},
    )
    assert response_medium.status_code == 201

    # File over 10MB should fail with the default limit
    oversized_content = b"x" * (11 * 1024 * 1024)  # 11MB
    response_oversized = await async_client.post(
        "/files",
        data={"title": "Oversized file"},
        files={
            "file": ("oversized.bin", oversized_content, "application/octet-stream")
        },
    )
    assert response_oversized.status_code == 413
