from dataclasses import dataclass
from pathlib import Path

from src.application.errors import ProcessingError
from src.application.ports import AlertRepository, FileRepository, StorageGateway
from src.domain.models import AlertRecord, FileRecord


SUSPICIOUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".js"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
PDF_MIME_TYPES = {"application/pdf", "application/octet-stream"}
MISSING_STORED_FILE_DETAILS = "stored file not found during metadata extraction"


@dataclass(slots=True)
class WorkerPipelineStep:
    task_name: str
    file_id: str


class ScanFileForThreatsUseCase:
    def __init__(self, file_repository: FileRepository) -> None:
        self.file_repository = file_repository

    async def execute(self, file_id: str) -> WorkerPipelineStep | None:
        file_record = await self.file_repository.get_file(file_id)
        if file_record is None:
            raise ProcessingError(f"File not found during threat scan: {file_id}")

        reasons = _collect_scan_reasons(file_record)
        updated_record = await self.file_repository.save_scan_result(
            file_id,
            processing_status="processing",
            scan_status="suspicious" if reasons else "clean",
            scan_details=", ".join(reasons) if reasons else "no threats found",
            requires_attention=bool(reasons),
        )
        if updated_record is None:
            raise ProcessingError(f"Failed to save scan result: {file_id}")

        return WorkerPipelineStep(task_name="extract_file_metadata", file_id=file_id)


class ExtractFileMetadataUseCase:
    def __init__(
        self,
        file_repository: FileRepository,
        storage_gateway: StorageGateway,
    ) -> None:
        self.file_repository = file_repository
        self.storage_gateway = storage_gateway

    async def execute(self, file_id: str) -> WorkerPipelineStep | None:
        file_record = await self.file_repository.get_file(file_id)
        if file_record is None:
            raise ProcessingError(
                f"File not found during metadata extraction: {file_id}"
            )

        stored_path = self.storage_gateway.resolve_path(file_record.stored_name)
        if stored_path is None:
            # Terminal failure: stored file missing
            # Preserve scan_status vocabulary - do NOT set to "failed" (threat model T-03-03-02)
            updated_record = await self.file_repository.save_metadata_result(
                file_id,
                processing_status="failed",
                metadata_json=file_record.metadata_json,
                scan_status=file_record.scan_status,  # Preserve existing scan_status
                scan_details=MISSING_STORED_FILE_DETAILS,
            )
            if updated_record is None:
                raise ProcessingError(
                    f"Failed to save metadata result for missing file: {file_id}"
                )
            return WorkerPipelineStep(task_name="send_file_alert", file_id=file_id)

        metadata = _build_file_metadata(file_record, self.storage_gateway, stored_path)
        updated_record = await self.file_repository.save_metadata_result(
            file_id,
            processing_status="processed",
            metadata_json=metadata,
        )
        if updated_record is None:
            raise ProcessingError(f"Failed to save metadata result: {file_id}")

        return WorkerPipelineStep(task_name="send_file_alert", file_id=file_id)


class SendFileAlertUseCase:
    def __init__(
        self,
        file_repository: FileRepository,
        alert_repository: AlertRepository,
    ) -> None:
        self.file_repository = file_repository
        self.alert_repository = alert_repository

    async def execute(self, file_id: str) -> AlertRecord | None:
        file_record = await self.file_repository.get_file(file_id)
        if file_record is None:
            raise ProcessingError(f"File not found during alert send: {file_id}")

        level, message = _build_alert_payload(file_record)
        return await self.alert_repository.create_alert(
            file_id=file_id,
            level=level,
            message=message,
        )


def _collect_scan_reasons(file_record: FileRecord) -> list[str]:
    reasons: list[str] = []
    extension = Path(file_record.original_name).suffix.lower()

    if extension in SUSPICIOUS_EXTENSIONS:
        reasons.append(f"suspicious extension {extension}")

    if file_record.size > MAX_FILE_SIZE_BYTES:
        reasons.append("file is larger than 10 MB")

    if extension == ".pdf" and file_record.mime_type not in PDF_MIME_TYPES:
        reasons.append("pdf extension does not match mime type")

    return reasons


def _build_file_metadata(
    file_record: FileRecord,
    storage_gateway: StorageGateway,
    stored_path: Path,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "extension": Path(file_record.original_name).suffix.lower(),
        "size_bytes": file_record.size,
        "mime_type": file_record.mime_type,
    }

    if file_record.mime_type.startswith("text/"):
        content = storage_gateway.read_text(stored_path.name, encoding="utf-8")
        metadata["line_count"] = len(content.splitlines())
        metadata["char_count"] = len(content)
    elif file_record.mime_type == "application/pdf":
        content = storage_gateway.read_bytes(stored_path.name)
        metadata["approx_page_count"] = max(content.count(b"/Type /Page"), 1)

    return metadata


def _build_alert_payload(file_record: FileRecord) -> tuple[str, str]:
    if file_record.processing_status == "failed":
        return "critical", "File processing failed"

    if file_record.requires_attention:
        return "warning", f"File requires attention: {file_record.scan_details}"

    return "info", "File processed successfully"
