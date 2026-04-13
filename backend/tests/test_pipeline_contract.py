from pathlib import Path

import pytest

from tests.support.worker_process import running_worker


pytestmark = pytest.mark.usefixtures("clean_database")


@pytest.mark.asyncio
async def test_pipeline_contract_helper_observes_uploaded_before_worker_runs(
    async_client,
    queue_backend_tasks,
):
    response = await async_client.post(
        "/files",
        data={"title": "Queued file"},
        files={"file": ("queued.txt", b"queued body", "text/plain")},
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["processing_status"] == "uploaded"
    assert queue_backend_tasks.calls == [payload["id"]]


@pytest.mark.real_worker
@pytest.mark.asyncio
async def test_real_worker_clean_upload_reaches_processed_info_alert(
    async_client,
    poller,
    worker_env,
):
    create_response = await async_client.post(
        "/files",
        data={"title": "Clean file"},
        files={"file": ("clean.txt", b"hello\nworld\n", "text/plain")},
    )
    payload = create_response.json()

    assert create_response.status_code == 201
    assert payload["processing_status"] == "uploaded"

    with running_worker(env=worker_env(), timeout=20.0):
        file_item = await poller.wait_for_file_state(
            payload["id"],
            processing_status="processed",
            scan_status="clean",
            requires_attention=False,
            timeout=20.0,
        )
        alerts = await poller.wait_for_alert_count(payload["id"], 1, timeout=20.0)

    assert file_item.metadata_json is not None
    assert file_item.metadata_json["line_count"] == 2
    assert alerts[0].level == "info"
    assert alerts[0].message == "File processed successfully"


@pytest.mark.real_worker
@pytest.mark.asyncio
async def test_real_worker_suspicious_upload_sets_attention_and_warning_alert(
    async_client,
    poller,
    worker_env,
):
    create_response = await async_client.post(
        "/files",
        data={"title": "Suspicious file"},
        files={"file": ("danger.exe", b"MZ", "application/octet-stream")},
    )
    payload = create_response.json()

    with running_worker(env=worker_env(), timeout=20.0):
        file_item = await poller.wait_for_file_state(
            payload["id"],
            processing_status="processed",
            scan_status="suspicious",
            requires_attention=True,
            timeout=20.0,
        )
        alerts = await poller.wait_for_alert_count(payload["id"], 1, timeout=20.0)

    assert "suspicious extension .exe" in (file_item.scan_details or "")
    assert alerts[0].level == "warning"
    assert alerts[0].message.startswith("File requires attention:")


@pytest.mark.real_worker
@pytest.mark.asyncio
async def test_real_worker_missing_stored_file_becomes_failed_with_critical_alert(
    async_client,
    poller,
    storage_dir,
    worker_env,
):
    create_response = await async_client.post(
        "/files",
        data={"title": "Missing blob"},
        files={"file": ("missing.txt", b"temporary", "text/plain")},
    )
    payload = create_response.json()

    stored_path = Path(storage_dir, f"{payload['id']}.txt")
    stored_path.unlink()

    with running_worker(env=worker_env(), timeout=20.0):
        file_item = await poller.wait_for_file_state(
            payload["id"],
            processing_status="failed",
            requires_attention=False,
            timeout=20.0,
        )
        alerts = await poller.wait_for_alert_count(payload["id"], 1, timeout=20.0)

    assert file_item.scan_details == "stored file not found during metadata extraction"
    assert alerts[0].level == "critical"
    assert alerts[0].message == "File processing failed"
