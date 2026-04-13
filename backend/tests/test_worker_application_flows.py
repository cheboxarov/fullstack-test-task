from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.domain.models import AlertRecord, FileRecord
from src.application.use_cases.file_processing import (
    ExtractFileMetadataUseCase,
    ScanFileForThreatsUseCase,
    SendFileAlertUseCase,
)


NOW = datetime(2026, 4, 11, tzinfo=timezone.utc)


class FakeFileRepository:
    def __init__(self, *file_records: FileRecord) -> None:
        self.files = {file_record.id: file_record for file_record in file_records}

    async def get_file(self, file_id: str) -> FileRecord | None:
        return self.files.get(file_id)

    async def save_scan_result(
        self,
        file_id: str,
        *,
        processing_status: str,
        scan_status: str | None,
        scan_details: str | None,
        requires_attention: bool,
    ) -> FileRecord | None:
        file_record = self.files.get(file_id)
        if file_record is None:
            return None

        updated_record = replace(
            file_record,
            processing_status=processing_status,
            scan_status=scan_status,
            scan_details=scan_details,
            requires_attention=requires_attention,
        )
        self.files[file_id] = updated_record
        return updated_record

    async def save_metadata_result(
        self,
        file_id: str,
        *,
        processing_status: str,
        metadata_json: dict[str, object] | None,
        scan_status: str | None = None,
        scan_details: str | None = None,
    ) -> FileRecord | None:
        file_record = self.files.get(file_id)
        if file_record is None:
            return None

        updated_record = replace(
            file_record,
            processing_status=processing_status,
            metadata_json=metadata_json,
            scan_status=file_record.scan_status if scan_status is None else scan_status,
            scan_details=file_record.scan_details
            if scan_details is None
            else scan_details,
        )
        self.files[file_id] = updated_record
        return updated_record


class FakeAlertRepository:
    def __init__(self) -> None:
        self.created: list[AlertRecord] = []

    async def create_alert(
        self,
        *,
        file_id: str,
        level: str,
        message: str,
    ) -> AlertRecord:
        alert_record = AlertRecord(
            id=len(self.created) + 1,
            file_id=file_id,
            level=level,
            message=message,
            created_at=NOW,
        )
        self.created.append(alert_record)
        return alert_record


class FakeStorageGateway:
    def __init__(
        self,
        *,
        text_files: dict[str, str] | None = None,
        binary_files: dict[str, bytes] | None = None,
    ) -> None:
        self.text_files = text_files or {}
        self.binary_files = binary_files or {}

    def resolve_path(self, stored_name: str) -> Path | None:
        if stored_name in self.text_files or stored_name in self.binary_files:
            return Path(stored_name)
        return None

    def read_text(self, stored_name: str, encoding: str = "utf-8") -> str:
        return self.text_files[stored_name]

    def read_bytes(self, stored_name: str) -> bytes:
        return self.binary_files[stored_name]


def build_file_record(
    file_id: str,
    *,
    original_name: str,
    stored_name: str,
    mime_type: str,
    size: int,
    processing_status: str = "uploaded",
    scan_status: str | None = None,
    scan_details: str | None = None,
    metadata_json: dict[str, object] | None = None,
    requires_attention: bool = False,
) -> FileRecord:
    return FileRecord(
        id=file_id,
        title=f"title-{file_id}",
        original_name=original_name,
        stored_name=stored_name,
        mime_type=mime_type,
        size=size,
        processing_status=processing_status,
        scan_status=scan_status,
        scan_details=scan_details,
        metadata_json=metadata_json,
        requires_attention=requires_attention,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_scan_use_case_preserves_current_suspicious_rules() -> None:
    file_repository = FakeFileRepository(
        build_file_record(
            "clean-threshold",
            original_name="report.txt",
            stored_name="report.txt",
            mime_type="text/plain",
            size=10 * 1024 * 1024,
        ),
        build_file_record(
            "extension-and-size",
            original_name="runner.js",
            stored_name="runner.js",
            mime_type="text/javascript",
            size=(10 * 1024 * 1024) + 1,
        ),
        build_file_record(
            "pdf-mismatch",
            original_name="paper.pdf",
            stored_name="paper.pdf",
            mime_type="text/plain",
            size=1024,
        ),
    )
    use_case = ScanFileForThreatsUseCase(file_repository=file_repository)

    clean_step = await use_case.execute("clean-threshold")
    combined_step = await use_case.execute("extension-and-size")
    pdf_step = await use_case.execute("pdf-mismatch")

    clean_record = file_repository.files["clean-threshold"]
    combined_record = file_repository.files["extension-and-size"]
    pdf_record = file_repository.files["pdf-mismatch"]

    assert clean_step.task_name == "extract_file_metadata"
    assert clean_step.file_id == "clean-threshold"
    assert clean_record.processing_status == "processing"
    assert clean_record.scan_status == "clean"
    assert clean_record.scan_details == "no threats found"
    assert clean_record.requires_attention is False

    assert combined_step.task_name == "extract_file_metadata"
    assert combined_step.file_id == "extension-and-size"
    assert combined_record.scan_status == "suspicious"
    assert (
        combined_record.scan_details
        == "suspicious extension .js, file is larger than 10 MB"
    )
    assert combined_record.requires_attention is True

    assert pdf_step.task_name == "extract_file_metadata"
    assert pdf_step.file_id == "pdf-mismatch"
    assert pdf_record.scan_status == "suspicious"
    assert pdf_record.scan_details == "pdf extension does not match mime type"
    assert pdf_record.requires_attention is True


@pytest.mark.asyncio
async def test_extract_metadata_use_case_preserves_text_pdf_and_missing_blob_behavior() -> (
    None
):
    file_repository = FakeFileRepository(
        build_file_record(
            "text-file",
            original_name="notes.txt",
            stored_name="notes.txt",
            mime_type="text/plain",
            size=12,
            scan_status="clean",
            scan_details="no threats found",
        ),
        build_file_record(
            "pdf-file",
            original_name="deck.pdf",
            stored_name="deck.pdf",
            mime_type="application/pdf",
            size=64,
            scan_status="clean",
            scan_details="no threats found",
        ),
        build_file_record(
            "missing-existing-status",
            original_name="ghost.txt",
            stored_name="ghost.txt",
            mime_type="text/plain",
            size=10,
            scan_status="suspicious",
            scan_details="suspicious extension .txt",
            metadata_json={"previous": "value"},
            requires_attention=True,
        ),
        build_file_record(
            "missing-no-status",
            original_name="lost.bin",
            stored_name="lost.bin",
            mime_type="application/octet-stream",
            size=10,
        ),
    )
    storage_gateway = FakeStorageGateway(
        text_files={"notes.txt": "hello\nworld\n"},
        binary_files={"deck.pdf": b"%PDF /Type /Page 1 /Type /Page 2"},
    )
    use_case = ExtractFileMetadataUseCase(
        file_repository=file_repository,
        storage_gateway=storage_gateway,
    )

    text_step = await use_case.execute("text-file")
    pdf_step = await use_case.execute("pdf-file")
    missing_existing_step = await use_case.execute("missing-existing-status")
    missing_no_status_step = await use_case.execute("missing-no-status")

    text_record = file_repository.files["text-file"]
    pdf_record = file_repository.files["pdf-file"]
    missing_existing_record = file_repository.files["missing-existing-status"]
    missing_no_status_record = file_repository.files["missing-no-status"]

    assert text_step.task_name == "send_file_alert"
    assert text_step.file_id == "text-file"
    assert text_record.processing_status == "processed"
    assert text_record.metadata_json == {
        "extension": ".txt",
        "size_bytes": 12,
        "mime_type": "text/plain",
        "line_count": 2,
        "char_count": 12,
    }

    assert pdf_step.task_name == "send_file_alert"
    assert pdf_step.file_id == "pdf-file"
    assert pdf_record.processing_status == "processed"
    assert pdf_record.metadata_json == {
        "extension": ".pdf",
        "size_bytes": 64,
        "mime_type": "application/pdf",
        "approx_page_count": 2,
    }

    assert missing_existing_step.task_name == "send_file_alert"
    assert missing_existing_step.file_id == "missing-existing-status"
    assert missing_existing_record.processing_status == "failed"
    assert missing_existing_record.scan_status == "suspicious"
    assert (
        missing_existing_record.scan_details
        == "stored file not found during metadata extraction"
    )
    assert missing_existing_record.metadata_json == {"previous": "value"}

    assert missing_no_status_step.task_name == "send_file_alert"
    assert missing_no_status_step.file_id == "missing-no-status"
    assert missing_no_status_record.processing_status == "failed"
    assert missing_no_status_record.scan_status is None
    assert (
        missing_no_status_record.scan_details
        == "stored file not found during metadata extraction"
    )


@pytest.mark.asyncio
async def test_send_alert_use_case_preserves_exact_level_and_message_mapping() -> None:
    file_repository = FakeFileRepository(
        build_file_record(
            "success",
            original_name="ok.txt",
            stored_name="ok.txt",
            mime_type="text/plain",
            size=20,
            processing_status="processed",
            scan_status="clean",
            scan_details="no threats found",
        ),
        build_file_record(
            "warning",
            original_name="warn.js",
            stored_name="warn.js",
            mime_type="text/javascript",
            size=20,
            processing_status="processed",
            scan_status="suspicious",
            scan_details="suspicious extension .js",
            requires_attention=True,
        ),
        build_file_record(
            "failure",
            original_name="fail.bin",
            stored_name="fail.bin",
            mime_type="application/octet-stream",
            size=20,
            processing_status="failed",
            scan_status="failed",
            scan_details="stored file not found during metadata extraction",
        ),
    )
    alert_repository = FakeAlertRepository()
    use_case = SendFileAlertUseCase(
        file_repository=file_repository,
        alert_repository=alert_repository,
    )

    success_alert = await use_case.execute("success")
    warning_alert = await use_case.execute("warning")
    failure_alert = await use_case.execute("failure")

    assert len(alert_repository.created) == 3

    assert success_alert.level == "info"
    assert success_alert.message == "File processed successfully"

    assert warning_alert.level == "warning"
    assert warning_alert.message == "File requires attention: suspicious extension .js"

    assert failure_alert.level == "critical"
    assert failure_alert.message == "File processing failed"
