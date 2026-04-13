"""Tests for unified API error contract."""

import pytest


class TestApiErrorContract:
    """Verify all API errors follow unified envelope format."""

    async def test_file_not_found_returns_error_envelope(self, async_client):
        """GET /files/{missing} should return 404 with error envelope."""
        response = await async_client.get("/files/nonexistent-id")

        assert response.status_code == 404
        payload = response.json()
        assert "error" in payload
        assert payload["error"]["code"] == "file_not_found"
        assert "message" in payload["error"]
        assert payload["error"]["retryable"] is False
        assert "request_id" in payload["error"]

    async def test_stored_file_missing_returns_error_envelope(
        self, async_client, storage_dir
    ):
        """Download missing stored file should return 404 with error envelope."""
        # Create file, delete from storage, try download
        create_resp = await async_client.post(
            "/files",
            data={"title": "Ghost"},
            files={"file": ("ghost.txt", b"ghost", "text/plain")},
        )
        file_id = create_resp.json()["id"]

        # Delete from storage
        import os

        for f in os.listdir(storage_dir):
            if f.startswith(file_id):
                os.remove(os.path.join(storage_dir, f))

        response = await async_client.get(f"/files/{file_id}/download")

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "stored_file_missing"

    async def test_empty_upload_returns_error_envelope(self, async_client):
        """Empty file upload should return 400 with error envelope."""
        response = await async_client.post(
            "/files",
            data={"title": "Empty"},
            files={"file": ("empty.txt", b"", "text/plain")},
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload["error"]["code"] == "empty_upload"
        assert payload["error"]["retryable"] is False

    async def test_validation_error_returns_error_envelope(self, async_client):
        """Invalid input should return 422 with error envelope and field errors."""
        response = await async_client.post(
            "/files",
            data={"title": ""},  # Empty title
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["error"]["code"] == "validation_error"
        # Should have fields with error messages
        assert "fields" in payload["error"]

    async def test_request_id_header_matches_error_response(self, async_client):
        """X-Request-Id header should match error response request_id."""
        response = await async_client.get("/files/nonexistent")

        header_id = response.headers.get("x-request-id")
        payload_id = response.json()["error"]["request_id"]

        assert header_id == payload_id
        assert header_id is not None
        assert len(header_id) > 0
